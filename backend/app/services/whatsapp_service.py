"""WhatsApp Cloud API service - the primary messaging channel.

Kept in a separate service so the backend fully works without it.
Credentials come from environment variables only - never hard-coded,
never sent to the frontend and never written to logs.
"""
import hashlib
import hmac
import re
from typing import Optional

from .notification_service import notify

# WhatsApp rejects text bodies longer than 4096 characters.
MAX_TEXT_LENGTH = 4096


def to_whatsapp_number(phone: str, country_code: str = "91") -> str:
    """Digits-only international number, as the Cloud API expects.

    Reception stores numbers like ``9876543210``, ``09876543210`` or
    ``+91 98765 43210``; all become ``919876543210``.
    """
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and country_code:
        digits = country_code + digits
    return digits


class WhatsAppService:
    def __init__(self):
        from ..config import settings

        self._s = settings
        self.enabled = bool(
            self._s.WHATSAPP_ACCESS_TOKEN and self._s.WHATSAPP_PHONE_NUMBER_ID
        )

    # ---------- webhook security ----------
    @property
    def signature_required(self) -> bool:
        return bool(self._s.WHATSAPP_APP_SECRET)

    def verify_signature(self, raw_body: bytes, header: Optional[str]) -> bool:
        """Check Meta's ``X-Hub-Signature-256: sha256=<hex>`` header."""
        if not self.signature_required:
            return True
        if not header or not header.startswith("sha256="):
            return False
        expected = hmac.new(
            self._s.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, header[len("sha256="):])

    # ---------- public info (safe to show in the UI) ----------
    @property
    def business_number(self) -> str:
        return re.sub(r"\D", "", self._s.WHATSAPP_BUSINESS_NUMBER or "")

    @property
    def chat_link(self) -> str:
        """wa.me link that opens a chat with the college number."""
        if not self.business_number:
            return ""
        return f"https://wa.me/{self.business_number}?text=Hi"

    # ---------- sending ----------
    def send_text(self, to_number: str, message: str, db=None,
                  visitor_id: Optional[int] = None) -> bool:
        """Send an outbound WhatsApp text through the Cloud API.

        When ``db`` is given the attempt is logged in ``whatsapp_messages``.
        """
        if not self.enabled:
            return False
        import httpx

        to = to_whatsapp_number(to_number, self._s.WHATSAPP_DEFAULT_COUNTRY_CODE)
        body = (message or "")[:MAX_TEXT_LENGTH]
        url = (
            f"{self._s.WHATSAPP_API_BASE.rstrip('/')}/"
            f"{self._s.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        headers = {
            "Authorization": f"Bearer {self._s.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        wa_id, error = None, ""
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=20)
            data = resp.json() if resp.content else {}
            if resp.is_success:
                wa_id = ((data.get("messages") or [{}])[0]).get("id")
            else:
                err = data.get("error") or {}
                error = f"HTTP {resp.status_code}: {err.get('message', resp.text[:200])}"
        except Exception as exc:  # network / JSON errors
            error = f"{type(exc).__name__}: {exc}"

        if error:
            # Only the status/error text is logged - never the token.
            print(f"[whatsapp] send to ...{to[-4:]} failed: {error}")
        if db is not None:
            from ..models import WhatsAppMessage

            db.add(
                WhatsAppMessage(
                    wa_message_id=wa_id,
                    direction="OUT",
                    phone=to,
                    msg_type="text",
                    body=body,
                    status="FAILED" if error else "SENT",
                    error=error[:500],
                    visitor_id=visitor_id,
                )
            )
            db.flush()
        return not error


# Simple memoized instance
_whatsapp = None


def get_whatsapp_service() -> WhatsAppService:
    global _whatsapp
    if _whatsapp is None:
        _whatsapp = WhatsAppService()
    return _whatsapp


def push_notification(db, visitor, message: str, ntype: str = "INFO"):
    """
    Notify a visitor through every available channel:
    - notification row + system chat message (always)
    - WhatsApp Cloud API (only when configured)

    Note: WhatsApp only delivers free-form text within 24 hours of the
    visitor's last message to the college number; outside that window Meta
    requires an approved message template.
    """
    notify(db, visitor, message, ntype)
    if get_whatsapp_service().enabled:
        get_whatsapp_service().send_text(
            visitor.phone, message, db=db, visitor_id=visitor.id
        )

"""WhatsApp Cloud API webhook - the primary messaging channel.

Parent WhatsApp -> Webhook -> Backend (AI + Queue + Workflow) -> WhatsApp API

  GET  /api/whatsapp/webhook   Meta's verification handshake
  POST /api/whatsapp/webhook   inbound messages + delivery statuses
  GET  /api/whatsapp/status    public, non-secret channel info (wa.me QR)
  GET  /api/whatsapp/messages  recent message log (staff only)

Security: optional X-Hub-Signature-256 check (WHATSAPP_APP_SECRET), size
limit, payload validation and duplicate-event protection. Replies are sent
in a background task so Meta gets its 200 OK quickly and does not retry.
"""
import json
import re
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, WhatsAppMessage
from ..security import require_staff
from ..services.qr_service import qr_data_uri
from ..services.whatsapp_bot import process_inbound
from ..services.whatsapp_service import get_whatsapp_service

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

# Meta's webhook payloads are small; anything bigger is rejected.
MAX_BODY_BYTES = 1_000_000
_warned_unsigned = False


@router.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    """GET verification used by Meta when the callback URL is configured."""
    if (
        hub_mode == "subscribe"
        and settings.WHATSAPP_VERIFY_TOKEN
        and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN
    ):
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


def _extract_text(msg: dict) -> str:
    mtype = msg.get("type")
    if mtype == "text":
        return (msg.get("text") or {}).get("body", "")
    if mtype == "button":
        return (msg.get("button") or {}).get("text", "")
    if mtype == "interactive":
        inter = msg.get("interactive") or {}
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return reply.get("title", "")
    return ""


def _store_inbound(db: Session, msg: dict) -> Optional[int]:
    """Validate + log one inbound message. Returns its row id, or None when
    it is invalid or a duplicate delivery of a message already stored."""
    wa_id = str(msg.get("id") or "")
    phone = re.sub(r"\D", "", str(msg.get("from") or ""))
    if not wa_id or not (8 <= len(phone) <= 15):
        return None
    if db.query(WhatsAppMessage.id).filter(WhatsAppMessage.wa_message_id == wa_id).first():
        return None  # duplicate webhook event
    row = WhatsAppMessage(
        wa_message_id=wa_id,
        direction="IN",
        phone=phone,
        msg_type=str(msg.get("type") or "unknown")[:20],
        body=_extract_text(msg)[:4096],
        status="RECEIVED",
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # same event arriving concurrently
        db.rollback()
        return None
    return row.id


def _apply_status(db: Session, status: dict) -> None:
    """Delivery receipts: sent / delivered / read / failed."""
    wa_id = status.get("id")
    new = str(status.get("status") or "").upper()
    if not wa_id or new not in ("SENT", "DELIVERED", "READ", "FAILED"):
        return
    row = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.wa_message_id == wa_id, WhatsAppMessage.direction == "OUT")
        .first()
    )
    if row is None:
        return
    row.status = new
    if new == "FAILED":
        errors = status.get("errors") or [{}]
        row.error = str(errors[0].get("title") or errors[0].get("message") or "")[:500]
    db.commit()


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Inbound messages from WhatsApp, answered by the shared AI service."""
    global _warned_unsigned
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    svc = get_whatsapp_service()
    if not svc.verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Invalid signature")
    if not svc.signature_required and not _warned_unsigned:
        _warned_unsigned = True
        print("[whatsapp] WHATSAPP_APP_SECRET is not set - webhook signatures "
              "are NOT verified (fine for local testing only)")

    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    if payload.get("object") not in (None, "whatsapp_business_account"):
        return {"status": "ignored"}

    queued = 0
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            # Ignore events for a different number on the same Meta app.
            target = (value.get("metadata") or {}).get("phone_number_id")
            if (
                target
                and settings.WHATSAPP_PHONE_NUMBER_ID
                and str(target) != settings.WHATSAPP_PHONE_NUMBER_ID
            ):
                continue
            for status in value.get("statuses") or []:
                if isinstance(status, dict):
                    _apply_status(db, status)
            for msg in value.get("messages") or []:
                if not isinstance(msg, dict):
                    continue
                row_id = _store_inbound(db, msg)
                if row_id:
                    background.add_task(process_inbound, row_id)
                    queued += 1

    return {"status": "received", "queued": queued}


@router.get("/status")
def status():
    """Channel info for the UI. Never includes tokens or secrets."""
    svc = get_whatsapp_service()
    link = svc.chat_link
    return {
        "enabled": svc.enabled,
        "primary": True,
        "signature_verification": svc.signature_required,
        "business_number": svc.business_number,
        "chat_link": link,
        "qr": qr_data_uri(link) if link else "",
        "webhook_path": "/api/whatsapp/webhook",
    }


@router.get("/messages")
def recent_messages(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Recent WhatsApp traffic for monitoring (staff only)."""
    rows = (
        db.query(WhatsAppMessage)
        .order_by(WhatsAppMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "direction": r.direction,
            "phone": r.phone,
            "type": r.msg_type,
            "body": r.body,
            "status": r.status,
            "error": r.error,
            "visitor_id": r.visitor_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]

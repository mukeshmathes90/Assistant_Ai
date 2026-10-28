"""Telegram Bot API client (optional channel).

Kept separate from the WhatsApp service, which is left untouched. Credentials
come from environment variables only - never hard-coded. Uses the HTTP Bot API
with long polling, so no public URL or webhook is required.
"""
from ..config import settings


class TelegramService:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.enabled = bool(self.token)
        self._api_base = settings.TELEGRAM_API_BASE.rstrip("/")
        self._base = f"{self._api_base}/bot{self.token}" if self.enabled else ""
        self._me = None
        self._me_checked = False

    def _get(self, method, params=None, timeout=30):
        import httpx

        resp = httpx.get(f"{self._base}/{method}", params=params or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, method, payload, timeout=30):
        import httpx

        resp = httpx.post(f"{self._base}/{method}", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def get_me(self):
        """Return the bot account info (cached), or None if unreachable."""
        if not self.enabled:
            return None
        if not self._me_checked:
            self._me_checked = True
            try:
                self._me = (self._get("getMe") or {}).get("result")
            except Exception:
                self._me = None
        return self._me

    def get_updates(self, offset=None, timeout=25):
        if not self.enabled:
            return []
        params = {"timeout": timeout, "allowed_updates": '["message"]'}
        if offset is not None:
            params["offset"] = offset
        try:
            data = self._get("getUpdates", params=params, timeout=timeout + 10)
            return data.get("result") or []
        except Exception:
            return []

    def send_text(self, chat_id, message):
        if not self.enabled:
            return False
        try:
            self._post(
                "sendMessage",
                {"chat_id": chat_id, "text": (message or "")[:4000]},
            )
            return True
        except Exception:
            return False

    @property
    def bot_username(self):
        me = self.get_me() or {}
        return me.get("username", "")

    @property
    def bot_url(self):
        username = self.bot_username
        return f"https://t.me/{username}" if username else ""


# Simple memoized instance (mirrors get_whatsapp_service)
_telegram = None


def get_telegram_service() -> TelegramService:
    global _telegram
    if _telegram is None:
        _telegram = TelegramService()
    return _telegram

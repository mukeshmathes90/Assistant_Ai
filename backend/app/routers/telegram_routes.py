"""Telegram bot endpoints (status / bot QR for the reception desk)."""
from fastapi import APIRouter, Depends

from ..models import User
from ..security import require_staff
from ..services.qr_service import qr_data_uri
from ..services.telegram_service import get_telegram_service

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


@router.get("/status")
def status(user: User = Depends(require_staff)):
    """Return bot info and a scannable QR pointing at the Telegram bot."""
    svc = get_telegram_service()
    bot_url = svc.bot_url
    return {
        "enabled": svc.enabled,
        "bot_username": svc.bot_username,
        "bot_url": bot_url,
        "qr": qr_data_uri(bot_url) if bot_url else "",
    }

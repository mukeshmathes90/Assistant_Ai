"""Telegram bot: long-polling loop and message handling.

Adds Telegram as a secondary channel (WhatsApp is the primary one) for the
same AI assistant. It reuses the existing AI service and live queue data
(visitors/queues/stages), so the dashboard stays in sync.

Flow:
  /start            -> welcome + ask for the registered mobile number
  <mobile number>   -> link this Telegram chat to that Visitor and show status
  any other text     -> answered by the shared AI service (with live data)
  /status /help /unlink
"""
import threading

from ..config import settings
from ..database import SessionLocal
from ..models import ChatMessage, TelegramSession
from .ai_service import get_ai_service, load_history
from .messaging import (
    find_visitor_by_phone,
    live_summary,
    looks_like_phone,
    normalize_phone,
)
from .telegram_service import get_telegram_service

_thread = None
_stop = threading.Event()

WELCOME = (
    "Welcome to {college} Admission Assistant.\n\n"
    "I can answer admission questions (courses, documents, eligibility, "
    "hostel, transport, placement ...) and show your live queue status.\n\n"
    "To link your visit, send the mobile number you registered at the "
    "reception (e.g. 9876543210).\n\n"
    "Commands: /status  /help  /unlink"
)


# Shared with the WhatsApp channel (see messaging.py).
_normalize_phone = normalize_phone
_looks_like_phone = looks_like_phone
_find_visitor_by_phone = find_visitor_by_phone
_live_summary = live_summary


def _get_session(db, chat_id: str, username: str) -> TelegramSession:
    session = (
        db.query(TelegramSession)
        .filter(TelegramSession.chat_id == chat_id)
        .first()
    )
    if session is None:
        session = TelegramSession(chat_id=chat_id, username=username or "")
        db.add(session)
        db.commit()
        db.refresh(session)
    elif username and session.username != username:
        session.username = username
        db.commit()
    return session


def handle_update(db, update: dict) -> None:
    """Process one Telegram update and reply through the Bot API."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id", "") or "")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return

    username = (message.get("from") or {}).get("username", "") or ""
    session = _get_session(db, chat_id, username)
    visitor = session.visitor
    lower = text.lower()

    if lower in ("/start", "/help", "start", "help"):
        if visitor:
            reply = (
                f"Hi {visitor.full_name}!\n\n{_live_summary(db, visitor)}\n\n"
                "Ask me anything about your admission or documents."
            )
        else:
            reply = WELCOME.format(college=settings.COLLEGE_NAME)
    elif lower in ("/unlink", "unlink"):
        session.visitor_id = None
        db.commit()
        visitor = None
        reply = (
            "Unlinked. Send your registered mobile number to link again."
        )
    elif lower in ("/status", "status"):
        if visitor:
            reply = _live_summary(db, visitor)
        else:
            reply = (
                "I don't have your registration yet. Send the mobile number "
                "you used at the reception, e.g. 9876543210."
            )
    elif _looks_like_phone(text):
        found = _find_visitor_by_phone(db, text)
        if found:
            session.visitor_id = found.id
            db.commit()
            session.visitor = found
            visitor = found
            reply = (
                f"Linked to {found.visitor_code} - {found.full_name}.\n\n"
                f"{_live_summary(db, found)}\n\n"
                "Ask me anything about documents, fees, courses, hostel, "
                "transport, placement or your status."
            )
        else:
            reply = (
                "I couldn't find a registration with that number.\n"
                "Please register at the reception desk first, or ask me a "
                "general admission question (type /help)."
            )
    else:
        history = load_history(db, visitor.id) if visitor else None
        reply = get_ai_service().answer(db, text, visitor, history=history)

    if visitor:
        db.add(ChatMessage(visitor_id=visitor.id, sender="USER", message=text))
        db.add(ChatMessage(visitor_id=visitor.id, sender="AI", message=reply))
        db.commit()

    get_telegram_service().send_text(chat_id, reply)


def _poll_loop() -> None:
    svc = get_telegram_service()
    if not svc.enabled:
        return
    me = svc.get_me()
    if not me:
        print("[telegram] token invalid or network unavailable - bot not started")
        return
    print(f"[telegram] bot @{me.get('username', '?')} is listening (long polling)")

    offset = None
    while not _stop.is_set():
        updates = svc.get_updates(offset=offset, timeout=25)
        for update in updates:
            offset = (update.get("update_id") or 0) + 1
            db = SessionLocal()
            try:
                handle_update(db, update)
            except Exception as exc:  # keep the loop alive on bad messages
                db.rollback()
                print(f"[telegram] update error: {exc}")
            finally:
                db.close()


def start_telegram_bot() -> None:
    """Start the background polling thread (no-op if disabled/unconfigured)."""
    global _thread
    if not settings.TELEGRAM_POLLING:
        return
    if not get_telegram_service().enabled:
        return
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(
        target=_poll_loop, name="telegram-poll", daemon=True
    )
    _thread.start()


def stop_telegram_bot() -> None:
    _stop.set()

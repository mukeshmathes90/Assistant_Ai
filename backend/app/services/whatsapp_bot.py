"""WhatsApp message handling (primary channel).

Mirrors the Telegram bot, but WhatsApp tells us the sender's number, so a
registered visitor is recognised automatically - no linking step needed.

  help / menu / start  -> welcome (+ live status when registered)
  status               -> live queue summary
  any other text       -> shared AI service (Gemini) with the college
                          knowledge base, live visitor context and memory
"""
from ..config import settings
from ..database import SessionLocal
from ..models import ChatMessage, WhatsAppMessage
from .ai_service import get_ai_service, load_history
from .messaging import find_visitor_by_phone, live_summary
from .whatsapp_service import get_whatsapp_service

# Longer messages are cut before they reach the AI service.
MAX_INPUT_LENGTH = 1000

WELCOME = (
    "Welcome to {college} Admission Assistant on WhatsApp.\n\n"
    "Ask me about courses, eligibility, documents, fees, hostel, transport "
    "or placement.\n\n"
    "If you registered at the reception with this WhatsApp number, I can "
    "also show your live queue status - just type *status*."
)

UNSUPPORTED = (
    "Sorry, I can only read text messages right now. Please type your "
    "question (for example: Is hostel available?)."
)


def _phone_history(db, phone: str, before_id: int, limit: int = 14) -> list:
    """Conversation memory for numbers not registered at the reception."""
    rows = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.phone == phone,
            WhatsAppMessage.id < before_id,
            WhatsAppMessage.status.in_(["REPLIED", "SENT", "DELIVERED", "READ"]),
        )
        .order_by(WhatsAppMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "role": "user" if r.direction == "IN" else "assistant",
            "content": r.body,
        }
        for r in reversed(rows)
        if r.body
    ]


def build_reply(db, inbound: WhatsAppMessage, visitor) -> str:
    if inbound.msg_type not in ("text", "button", "interactive"):
        return UNSUPPORTED

    text = (inbound.body or "").strip()[:MAX_INPUT_LENGTH]
    lower = text.lower().lstrip("/")

    if lower in ("help", "menu", "start"):
        welcome = WELCOME.format(college=settings.COLLEGE_NAME)
        if visitor:
            return f"Hi {visitor.full_name}!\n\n{live_summary(db, visitor)}\n\n{welcome}"
        return welcome
    if lower in ("status", "my status"):
        if visitor:
            return live_summary(db, visitor)
        return (
            "I couldn't find a registration for this WhatsApp number.\n"
            "Please register at the reception desk with this number, or ask "
            "me any admission question."
        )

    if visitor:
        history = load_history(db, visitor.id)
    else:
        history = _phone_history(db, inbound.phone, inbound.id)
    return get_ai_service().answer(db, text, visitor, history=history)


def process_inbound(message_row_id: int) -> None:
    """Answer one stored inbound message (runs after the webhook returns)."""
    db = SessionLocal()
    try:
        inbound = db.get(WhatsAppMessage, message_row_id)
        if inbound is None or inbound.status != "RECEIVED":
            return
        visitor = find_visitor_by_phone(db, inbound.phone, include_cancelled=False)
        inbound.visitor_id = visitor.id if visitor else None

        reply = build_reply(db, inbound, visitor)

        if visitor and inbound.body:
            db.add(ChatMessage(visitor_id=visitor.id, sender="USER", message=inbound.body))
            db.add(ChatMessage(visitor_id=visitor.id, sender="AI", message=reply))

        sent = get_whatsapp_service().send_text(
            inbound.phone, reply, db=db,
            visitor_id=visitor.id if visitor else None,
        )
        if sent:
            inbound.status = "REPLIED"
        elif not get_whatsapp_service().enabled:
            inbound.status = "FAILED"
            inbound.error = "WhatsApp is not configured (token / phone number ID missing)"
        else:
            inbound.status = "FAILED"
            inbound.error = "Reply could not be sent - see the OUT row"
        db.commit()
    except Exception as exc:  # never let one bad message break the webhook
        db.rollback()
        print(f"[whatsapp] processing error: {type(exc).__name__}: {exc}")
        try:
            row = db.get(WhatsAppMessage, message_row_id)
            if row is not None:
                row.status = "FAILED"
                row.error = f"{type(exc).__name__}: {exc}"[:500]
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()

"""Parent chat + visitor self-service routes (used by the chat UI)."""
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChatMessage, Visitor
from ..schemas import ChatMessageOut, ChatSendIn, SessionOut, VisitorOut
from ..services.ai_service import get_ai_service, load_history
from ..services.helpers import serialize_visitor

router = APIRouter(tags=["Chat"])


def _normalize_phone(phone: str) -> str:
    phone = phone.replace(" ", "").replace("+", "")
    if phone.startswith("0"):
        phone = phone[1:]
    return phone


def _find_visitor(db: Session, phone: str):
    phone_n = _normalize_phone(phone)
    return (
        db.query(Visitor)
        .filter(Visitor.status != "CANCELLED")
        .filter(
            or_(
                Visitor.phone == phone,
                Visitor.phone == phone_n,
                Visitor.phone == "+" + phone_n,
            )
        )
        .order_by(Visitor.id.desc())
        .first()
    )


def _ensure_welcome(db: Session, visitor: Visitor):
    """Add a first AI message so the chat always opens with a welcome."""
    has_message = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.visitor_id == visitor.id,
            ChatMessage.sender == "AI",
        )
        .first()
    )
    if has_message:
        return
    ai = get_ai_service()
    welcome = ai.answer(db, "hi", visitor)
    db.add(
        ChatMessage(
            visitor_id=visitor.id, sender="AI", message=welcome
        )
    )
    db.commit()


@router.get("/api/chat/session")
def chat_session(
    phone: str,
    db: Session = Depends(get_db),
):
    visitor = _find_visitor(db, phone)
    messages = []
    if visitor:
        _ensure_welcome(db, visitor)
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.visitor_id == visitor.id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        messages = [
            ChatMessageOut(
                id=m.id,
                sender=m.sender,
                message=m.message,
                created_at=m.created_at,
            )
            for m in rows
        ]
    return SessionOut(
        visitor=serialize_visitor(db, visitor) if visitor else None,
        messages=messages,
    )


@router.post("/api/chat/send")
def chat_send(
    data: ChatSendIn,
    db: Session = Depends(get_db),
):
    visitor = _find_visitor(db, data.phone)
    ai = get_ai_service()
    if visitor is None:
        reply = ai.answer(db, data.message, None)
        return {
            "id": 0,
            "sender": "AI",
            "message": reply,
            "created_at": None,
            "visitor_found": False,
        }
    history = load_history(db, visitor.id)
    user_msg = ChatMessage(
        visitor_id=visitor.id, sender="USER", message=data.message
    )
    db.add(user_msg)
    db.flush()

    reply = ai.answer(db, data.message, visitor, history=history)

    ai_msg = ChatMessage(
        visitor_id=visitor.id, sender="AI", message=reply
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    return {
        "id": ai_msg.id,
        "sender": "AI",
        "message": ai_msg.message,
        "created_at": ai_msg.created_at,
        "visitor_found": True,
        "visitor": serialize_visitor(db, visitor),
    }


@router.get("/api/chat/visitors")
def find_visitors(
    phone: str = "",
    code: str = "",
    db: Session = Depends(get_db),
):
    """Resolve a phone/visitor code to a visitor (chat switcher)."""
    query = db.query(Visitor)
    if phone:
        phone_n = _normalize_phone(phone)
        query = query.filter(
            or_(
                Visitor.phone == phone,
                Visitor.phone == phone_n,
                Visitor.phone == "+" + phone_n,
            )
        )
    if code:
        query = query.filter(Visitor.visitor_code == code)
    visitors = query.order_by(Visitor.id.desc()).limit(20).all()
    return {"visitors": [serialize_visitor(db, v) for v in visitors]}


@router.get("/api/kb/active")
def public_kb(db: Session = Depends(get_db)):
    """Public knowledge used by the chat 'help' panel (read-only FAQs)."""
    from ..models import FAQ

    faqs = db.query(FAQ).filter(FAQ.is_active.is_(True)).limit(30).all()
    return {"faqs": [{"question": f.question, "answer": f.answer} for f in faqs]}


# Backwards-compatible marker endpoint
@router.get("/api/chat/test")
def chat_test(db: Session = Depends(get_db)):
    return {"ok": True}
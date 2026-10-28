"""Notification service - records notifications and mirrors them into chat."""
from ..models import ChatMessage, Notification, Visitor


def notify(db, visitor: Visitor, message: str, ntype: str = "INFO"):
    """Create a notification row + a system chat message for the visitor."""
    if visitor is None:
        return None
    notif = Notification(visitor_id=visitor.id, message=message, ntype=ntype)
    db.add(notif)
    db.add(
        ChatMessage(
            visitor_id=visitor.id, sender="SYSTEM", message=message
        )
    )
    db.flush()
    return notif
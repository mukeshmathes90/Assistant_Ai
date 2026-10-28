"""Helpers shared by the messaging channels (WhatsApp primary, Telegram).

Both bots look visitors up by the mobile number given at the reception and
show the same live queue summary, so the logic lives here once.
"""
import re

from ..models import Visitor
from .helpers import serialize_visitor


def normalize_phone(value: str) -> str:
    """Last 10 digits of a phone number (drops +91 / 0 prefixes, spaces)."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


def looks_like_phone(text: str) -> bool:
    digits = re.sub(r"\D", "", text or "")
    return 10 <= len(digits) <= 13


def find_visitor_by_phone(db, phone: str, include_cancelled: bool = True):
    """Most recent visitor registered with this number (any format)."""
    norm = normalize_phone(phone)
    if len(norm) < 10:
        return None
    query = db.query(Visitor)
    if not include_cancelled:
        query = query.filter(Visitor.status != "CANCELLED")
    for v in query.order_by(Visitor.id.desc()).all():
        if normalize_phone(v.phone) == norm:
            return v
    return None


def live_summary(db, visitor: Visitor) -> str:
    d = serialize_visitor(db, visitor)
    entry = d.current_queue_entry
    lines = [f"Visitor ID: {d.visitor_code} ({d.full_name})"]
    if d.current_stage_name:
        lines.append(f"Stage: {d.current_stage_name}")
    if entry:
        lines.append(f"Queue number: {entry.token_display}")
        if entry.position is not None:
            lines.append(f"People ahead: {entry.position}")
        lines.append(f"Status: {entry.status}")
    if d.room_name:
        lines.append(f"Room: {d.room_name}")
    if d.assigned_staff_name:
        lines.append(f"Staff: {d.assigned_staff_name}")
    if d.next_stage_name:
        lines.append(f"Next stage: {d.next_stage_name}")
    return "\n".join(lines)

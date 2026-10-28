"""Serialization helpers shared across routers."""
from sqlalchemy.orm import Session

from ..models import Visitor
from ..schemas import QueueEntryBriefOut, VisitorOut
from .queue_engine import queue_position
from .workflow_engine import next_stage


def serialize_visitor(db: Session, v: Visitor) -> VisitorOut:
    out = VisitorOut(
        id=v.id,
        visitor_code=v.visitor_code,
        full_name=v.full_name,
        phone=v.phone,
        purpose=v.purpose,
        department_id=v.department_id,
        department_name=v.department.name if v.department else None,
        remarks=v.remarks or "",
        status=v.status,
        current_workflow_id=v.current_workflow_id,
        current_workflow_name=v.current_workflow.name
        if v.current_workflow
        else None,
        current_stage_id=v.current_stage_id,
        current_stage_name=v.current_stage.name if v.current_stage else None,
        room_code=v.current_stage.room.code if v.current_stage and v.current_stage.room else None,
        room_name=v.current_stage.room.name if v.current_stage and v.current_stage.room else None,
        assigned_staff_name=v.current_stage.assigned_staff.user.full_name
        if v.current_stage and v.current_stage.assigned_staff
        else None,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )

    entry = v.current_queue_entry
    if entry is None:
        from ..models import QueueEntry

        entry = (
            db.query(QueueEntry)
            .filter(
                QueueEntry.visitor_id == v.id,
                QueueEntry.status.in_(["WAITING", "CALLED", "SERVING", "HOLD"]),
            )
            .order_by(QueueEntry.id.desc())
            .first()
        )

    if entry:
        pos = queue_position(db, entry)
        out.current_queue_entry = QueueEntryBriefOut(
            id=entry.id,
            token_display=entry.token_display,
            status=entry.status,
            queue_id=entry.queue_id,
            queue_name=entry.queue.name if entry.queue else "",
            position=pos if pos >= 0 else None,
        )
        setattr(out, "_position", pos)

    nxt = None
    if v.current_stage and v.current_stage.workflow:
        nxt = next_stage(db, v.current_stage.workflow, v.current_stage)
    if nxt:
        out.next_stage_name = nxt.name
        out.next_stage_room = nxt.room.name if nxt.room else None
    return out


def queue_entry_to_dict(e) -> dict:
    return {
        "id": e.id,
        "queue_id": e.queue_id,
        "visitor_id": e.visitor_id,
        "visitor_code": e.visitor.visitor_code,
        "visitor_name": e.visitor.full_name,
        "phone": e.visitor.phone,
        "token_display": e.token_display,
        "status": e.status,
        "position_order": e.position_order,
        "room_id": e.room_id,
        "room_code": e.room.code if e.room else None,
        "room_name": e.room.name if e.room else None,
        "called_at": e.called_at.isoformat() if e.called_at else None,
        "served_at": e.served_at.isoformat() if e.served_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "hold_reason": e.hold_reason or "",
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
"""Visitor lifecycle service.

Official state changes flow through this module ONLY. The AI never calls
these functions - it only reads state and answers questions.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    QueueEntry,
    User,
    Visitor,
    VisitorStageHistory,
)
from .queue_engine import (
    cancel_existing_entries,
    enqueue,
    get_or_create_queue,
    next_waiting_entry,
)
from .whatsapp_service import push_notification
from .workflow_engine import (
    find_workflow_for_visitor,
    first_stage,
    next_stage,
    previous_stage,
)


def get_next_visitor_code(db: Session) -> str:
    """Generate the next visitor code (V120 -> V121)."""
    codes = db.query(Visitor.visitor_code).all()
    max_num = 0
    for (code,) in codes:
        if code.startswith("V") and code[1:].isdigit():
            max_num = max(max_num, int(code[1:]))
    return f"V{max_num + 1}"


def register_visitor(
    db: Session,
    full_name: str,
    phone: str,
    purpose: str,
    department_id=None,
    remarks: str = "",
    needs_help_desk: bool = False,
    registered_by: User = None,
) -> Visitor:
    """Register a visitor and place them in the correct initial queue."""
    visitor = Visitor(
        visitor_code=get_next_visitor_code(db),
        full_name=full_name,
        phone=phone,
        purpose=purpose,
        department_id=department_id,
        remarks=remarks,
        status="ACTIVE",
        registered_by_user_id=registered_by.id if registered_by else None,
    )
    db.add(visitor)
    db.flush()

    workflow = find_workflow_for_visitor(
        db, department_id, purpose, needs_help_desk
    )
    if workflow is None:
        visitor.status = "CANCELLED"
        db.flush()
        return visitor

    stage = first_stage(db, workflow)
    if stage is None:
        visitor.status = "CANCELLED"
        db.flush()
        return visitor

    entry = enqueue(db, visitor, stage, actioned_by_user_id=visitor.registered_by_user_id)

    # Welcome notification
    room = stage.room
    staff = stage.assigned_staff
    msg = (
        f"Welcome to {settings.COLLEGE_NAME}, {visitor.full_name}!\n"
        f"Your Visitor ID is {visitor.visitor_code}.\n"
        f"Department: {visitor.department.name if visitor.department else 'Help Desk / Open'}\n"
        f"Current Stage: {stage.name}\n"
        f"Queue Number: {entry.token_display}\n"
        f"Location: {room.name if room else 'Main building'} ({room.code if room else ''})\n"
        f"Meeting: {staff.user.full_name if staff and staff.user else 'Assigned Officer'}\n\n"
        "Please wait for your number to be called. You can ask our AI assistant "
        "any question about documents, fees, or your status in the chat."
    )
    push_notification(db, visitor, msg, ntype="REGISTERED")
    db.commit()
    db.refresh(visitor)
    return visitor


def call_next(db: Session, queue_id: int, user: User):
    """Call the next WAITING visitor of a queue."""
    return _call_next_impl(db, queue_id, user)


def _call_next_impl(db: Session, queue_id: int, user: User):
    from ..models import Queue

    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if queue is None:
        return None, "Queue not found"

    entry = next_waiting_entry(db, queue)
    if entry is None:
        return None, "No waiting visitors in this queue"

    entry.status = "CALLED"
    entry.called_at = datetime.utcnow()
    entry.actioned_by_user_id = user.id
    entry.served_by_staff_id = (
        user.staff_profile.id if user.staff_profile else None
    )
    history = (
        db.query(VisitorStageHistory)
        .filter(
            VisitorStageHistory.queue_entry_id == entry.id,
            VisitorStageHistory.status == "PENDING",
        )
        .first()
    )
    if history:
        history.actioned_by_user_id = user.id

    visitor = entry.visitor
    visitor.current_stage_id = entry.queue.workflow_stage_id
    visitor.current_queue_entry_id = entry.id

    stage = entry.queue.stage
    room = stage.room
    staff = stage.assigned_staff
    who = (
        f"Meet: {staff.user.full_name}."
        if staff and staff.user
        else "Meet: assigned officer."
    )
    msg = (
        f"{visitor.visitor_code}: Your turn is now! {entry.token_display}\n"
        f"Please proceed to {room.name if room else 'the room'} "
        f"({room.code if room else ''}).\n{who}\nStage: {stage.name}"
    )
    push_notification(db, visitor, msg, ntype="CALLED")
    db.commit()
    db.refresh(entry)
    return entry, "OK"


def complete_stage(db: Session, entry_id: int, user: User):
    """Mark stage complete and auto-allocate the next workflow stage."""
    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if entry is None:
        return None, "Queue entry not found"
    if entry.status in ("COMPLETED", "CANCELLED", "SKIPPED"):
        return entry, "Entry already closed"

    visitor = entry.visitor
    stage = entry.queue.stage
    workflow = stage.workflow

    entry.status = "COMPLETED"
    entry.completed_at = datetime.utcnow()
    entry.served_by_staff_id = (
        user.staff_profile.id if user.staff_profile else None
    )
    entry.actioned_by_user_id = user.id

    history = (
        db.query(VisitorStageHistory)
        .filter(
            VisitorStageHistory.queue_entry_id == entry.id,
            VisitorStageHistory.status == "PENDING",
        )
        .first()
    )
    if history:
        history.status = "COMPLETED"
        history.completed_at = datetime.utcnow()
        history.actioned_by_user_id = user.id

    next_stg = next_stage(db, workflow, stage)
    if next_stg is not None:
        new_entry = enqueue(
            db, visitor, next_stg, actioned_by_user_id=user.id
        )
        room = next_stg.room
        msg = (
            f"{stage.name} completed for {visitor.visitor_code}. "
            f"Your next step is {next_stg.name}.\n"
            f"You have been added to the {next_stg.name} queue.\n"
            f"Queue Number: {new_entry.token_display}\n"
            f"Location: {room.name if room else 'Main building'} "
            f"({room.code if room else ''})\n"
            "Please wait for your turn."
        )
        push_notification(db, visitor, msg, ntype="NEXT_STAGE")
    else:
        # Workflow complete
        visitor.status = "COMPLETED"
        visitor.completed_at = datetime.utcnow()
        visitor.current_stage_id = None
        visitor.current_queue_entry_id = None
        msg = (
            f"Congratulations {visitor.visitor_code}! All admission stages are "
            "complete. Your admission is confirmed. Please collect your "
            "admission confirmation at the Admission Office."
        )
        push_notification(db, visitor, msg, ntype="COMPLETED")

    db.commit()
    db.refresh(entry)
    return entry, "OK"


def hold_visitor(db: Session, entry_id: int, user: User, reason: str = ""):
    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if entry is None:
        return None, "Queue entry not found"
    entry.status = "HOLD"
    entry.hold_reason = reason or "Held by staff"
    entry.actioned_by_user_id = user.id
    visitor = entry.visitor
    push_notification(
        db,
        visitor,
        f"{visitor.visitor_code}: your queue number {entry.token_display} has "
        f"been put on hold ({reason or 'please wait for staff'}).",
        ntype="HOLD",
    )
    db.commit()
    return entry, "OK"


def skip_visitor(db: Session, entry_id: int, user: User, reason: str = ""):
    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if entry is None:
        return None, "Queue entry not found"
    entry.status = "SKIPPED"
    entry.hold_reason = reason or "Skipped"
    entry.actioned_by_user_id = user.id
    db.commit()
    return entry, "OK"


def reassign_stage(
    db: Session, entry_id: int, new_stage_id: int, user: User, reason: str = ""
):
    """Move a visitor from the current queue to another workflow stage."""
    from ..models import WorkflowStage

    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if entry is None:
        return None, "Queue entry not found"
    new_stage = (
        db.query(WorkflowStage)
        .filter(WorkflowStage.id == new_stage_id, WorkflowStage.is_active.is_(True))
        .first()
    )
    if new_stage is None:
        return None, "Target stage not found"

    visitor = entry.visitor
    entry.status = "CANCELLED"
    entry.hold_reason = reason or "Reassigned"
    entry.actioned_by_user_id = user.id
    db.flush()

    cancel_existing_entries(db, visitor, keep_ids=[entry.id])

    new_entry = enqueue(db, visitor, new_stage, actioned_by_user_id=user.id)
    room = new_stage.room
    push_notification(
        db,
        visitor,
        f"{visitor.visitor_code}: you have been moved to {new_stage.name}.\n"
        f"New Queue Number: {new_entry.token_display}\n"
        f"Location: {room.name if room else 'Main building'} ({room.code if room else ''}).",
        ntype="REASSIGN",
    )
    db.commit()
    db.refresh(new_entry)
    return new_entry, "OK"


def get_previous_next(db: Session, entry: QueueEntry):
    stage = entry.queue.stage
    workflow = stage.workflow
    prev = previous_stage(db, workflow, stage) if workflow else None
    nxt = next_stage(db, workflow, stage) if workflow else None
    return prev, nxt
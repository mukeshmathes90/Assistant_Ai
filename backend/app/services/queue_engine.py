"""Queue engine - source of truth for all queue operations."""
from sqlalchemy.orm import Session

from ..models import Queue, QueueEntry, VisitorStageHistory, WorkflowStage


def get_or_create_queue(db: Session, stage: WorkflowStage) -> Queue:
    """Each workflow stage owns exactly one queue."""
    queue = (
        db.query(Queue).filter(Queue.workflow_stage_id == stage.id).first()
    )
    if queue is None:
        queue = Queue(
            workflow_stage_id=stage.id,
            name=f"{stage.name} Queue",
            current_token_number=0,
        )
        db.add(queue)
        db.flush()
    return queue


def _next_token(db: Session, queue: Queue) -> tuple:
    """Returns (token_number, token_display) for the next visitor."""
    queue.current_token_number += 1
    token_number = queue.current_token_number
    return token_number, f"{queue.stage.queue_code}-{token_number}"


def _last_position(db: Session, queue: Queue) -> int:
    """Ordering position for a new entry (after all non-cancelled entries)."""
    last = (
        db.query(QueueEntry)
        .filter(QueueEntry.queue_id == queue.id)
        .order_by(QueueEntry.position_order.desc())
        .first()
    )
    if last is None:
        return 1 if queue.current_token_number > 0 else 1
    return last.position_order + 1


def enqueue(
    db: Session,
    visitor,
    stage: WorkflowStage,
    actioned_by_user_id=None,
    append_history: bool = True,
) -> QueueEntry:
    """Place a visitor into the queue of the given stage."""
    queue = get_or_create_queue(db, stage)
    token_number, token_display = _next_token(db, queue)
    entry = QueueEntry(
        queue_id=queue.id,
        visitor_id=visitor.id,
        token_number=token_number,
        token_display=token_display,
        status="WAITING",
        position_order=_last_position(db, queue),
        room_id=stage.room_id,
        actioned_by_user_id=actioned_by_user_id,
    )
    db.add(entry)
    db.flush()

    visitor.current_workflow_id = stage.workflow_id
    visitor.current_stage_id = stage.id
    visitor.current_queue_entry_id = entry.id
    if visitor.status in ("CANCELLED", "COMPLETED"):
        visitor.status = "ACTIVE"
    visitor.completed_at = None

    if append_history:
        db.add(
            VisitorStageHistory(
                visitor_id=visitor.id,
                workflow_stage_id=stage.id,
                queue_entry_id=entry.id,
                status="PENDING",
            )
        )
    db.flush()
    return entry


def cancel_existing_entries(db: Session, visitor, keep_ids=None):
    """Cancels all non-completed queue entries of a visitor (used on reassign)."""
    ids = set(keep_ids or [])
    entries = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.visitor_id == visitor.id,
            QueueEntry.status.in_(
                ["WAITING", "CALLED", "SERVING", "HOLD"]
            ),
        )
        .all()
    )
    for e in entries:
        if e.id in ids:
            continue
        e.status = "CANCELLED"


def queue_position(db: Session, entry: QueueEntry) -> int:
    """Number of visitors ahead in the same queue (0 = next/being served)."""
    if entry.status in ("CALLED", "SERVING"):
        return 0
    if entry.status != "WAITING":
        return -1
    ahead = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == entry.queue_id,
            QueueEntry.status == "WAITING",
            QueueEntry.position_order < entry.position_order,
        )
        .count()
    )
    return ahead


def next_waiting_entry(db: Session, queue: Queue):
    """Earliest WAITING entry that hasn't been held/skipped."""
    return (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == queue.id,
            QueueEntry.status == "WAITING",
        )
        .order_by(QueueEntry.position_order.asc())
        .first()
    )


def stage_summary(db: Session, stage: WorkflowStage) -> dict:
    queue = get_or_create_queue(db, stage)
    waiting = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == queue.id,
            QueueEntry.status == "WAITING",
        )
        .count()
    )
    serving = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == queue.id,
            QueueEntry.status.in_(["CALLED", "SERVING"]),
        )
        .first()
    )
    today = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == queue.id,
            QueueEntry.status == "COMPLETED",
        )
    )
    completed_today = today.count()
    return {
        "queue_id": queue.id,
        "stage_id": stage.id,
        "stage_name": stage.name,
        "queue_name": queue.name,
        "waiting": waiting,
        "serving": serving.id if serving else None,
        "serving_token": serving.token_display if serving else None,
        "completed_today": completed_today,
    }
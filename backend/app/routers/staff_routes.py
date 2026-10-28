"""Staff routes: assigned queues + visitor processing actions.

Every action here maps to a real queue/workflow engine operation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Queue, QueueEntry, User, WorkflowStage
from ..schemas import StaffActionRequest
from ..security import get_current_user
from ..services import visitor_flow
from ..services.helpers import queue_entry_to_dict

router = APIRouter(prefix="/api/staff", tags=["Staff"])


def _staff_queues(db: Session, user: User):
    """Queues for the stages assigned to this staff member.

    ADMIN sees everything; otherwise the staff sees their assigned stages.
    """
    if user.role == "ADMIN":
        stages = (
            db.query(WorkflowStage)
            .filter(WorkflowStage.is_active.is_(True))
            .order_by(WorkflowStage.workflow_id, WorkflowStage.stage_order)
            .all()
        )
    else:
        if not user.staff_profile:
            raise HTTPException(
                status_code=403,
                detail="You do not have an assigned staff profile",
            )
        stages = user.staff_profile.assigned_stages

    queues = []
    for s in stages:
        if s.queue is None:
            continue
        queue = s.queue
        entries = (
            db.query(QueueEntry)
            .filter(
                QueueEntry.queue_id == queue.id,
                QueueEntry.status.in_(["WAITING", "CALLED", "SERVING", "HOLD"]),
            )
            .order_by(QueueEntry.position_order.asc())
            .all()
        )
        waiting_count = sum(1 for e in entries if e.status == "WAITING")
        queues.append(
            {
                "queue_id": queue.id,
                "queue_name": queue.name,
                "stage_id": s.id,
                "stage_name": s.name,
                "queue_code": s.queue_code,
                "workflow_id": s.workflow_id,
                "workflow_name": s.workflow.name,
                "room_code": s.room.code if s.room else None,
                "room_name": s.room.name if s.room else None,
                "waiting_count": waiting_count,
                "serving": next(
                    (
                        queue_entry_to_dict(e)
                        for e in entries
                        if e.status in ("CALLED", "SERVING")
                    ),
                    None,
                ),
                "entries": [queue_entry_to_dict(e) for e in entries],
            }
        )
    return queues


@router.get("/queues")
def my_queues(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _staff_queues(db, user)


@router.get("/stage-map")
def staff_stage_map(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All active stages the current user *may* reassign a visitor to."""
    stages = (
        db.query(WorkflowStage)
        .filter(WorkflowStage.is_active.is_(True))
        .order_by(WorkflowStage.workflow_id, WorkflowStage.stage_order)
        .all()
    )
    return [
        {
            "id": s.id,
            "name": s.name,
            "queue_code": s.queue_code,
            "workflow_name": s.workflow.name,
        }
        for s in stages
    ]


@router.get("/visitors/{visitor_id}")
def staff_visitor_detail(
    visitor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..models import Visitor, VisitorStageHistory
    from ..schemas import VisitorOut
    from ..services.helpers import serialize_visitor

    v = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail="Visitor not found")

    out = serialize_visitor(db, v)
    history = (
        db.query(VisitorStageHistory)
        .filter(VisitorStageHistory.visitor_id == v.id)
        .order_by(VisitorStageHistory.id.desc())
        .all()
    )
    prev, nxt = None, None
    if v.current_stage and v.current_stage.workflow:
        from ..services.workflow_engine import next_stage, previous_stage

        prev = previous_stage(db, v.current_stage.workflow, v.current_stage)
        nxt = next_stage(db, v.current_stage.workflow, v.current_stage)

    return {
        "visitor": VisitorOut.model_validate(out),
        "history": [
            {
                "stage": h.workflow_stage.name,
                "status": h.status,
                "entered_at": h.entered_at.isoformat() if h.entered_at else None,
                "completed_at": h.completed_at.isoformat()
                if h.completed_at
                else None,
            }
            for h in history
        ],
        "previous_stage": prev.name if prev else None,
        "next_stage": nxt.name if nxt else None,
    }


# ---------- Actions ----------

@router.post("/queues/{queue_id}/call-next")
def call_next(
    queue_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry, err = visitor_flow.call_next(db, queue_id, user)
    if err != "OK":
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "entry": queue_entry_to_dict(entry)}


@router.post("/entries/{entry_id}/start-serving")
def start_serving(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime

    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.status = "SERVING"
    entry.served_at = datetime.utcnow()
    entry.actioned_by_user_id = user.id
    db.commit()
    return {"ok": True, "entry": queue_entry_to_dict(entry)}


@router.post("/entries/{entry_id}/complete")
def complete(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry, err = visitor_flow.complete_stage(db, entry_id, user)
    if err != "OK":
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "entry": queue_entry_to_dict(entry)}


@router.post("/entries/{entry_id}/hold")
def hold(
    entry_id: int,
    data: StaffActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry, err = visitor_flow.hold_visitor(db, entry_id, user, data.reason)
    if err != "OK":
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "entry": queue_entry_to_dict(entry)}


@router.post("/entries/{entry_id}/skip")
def skip(
    entry_id: int,
    data: StaffActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry, err = visitor_flow.skip_visitor(db, entry_id, user, data.reason)
    if err != "OK":
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "entry": queue_entry_to_dict(entry)}


@router.post("/entries/{entry_id}/reassign")
def reassign(
    entry_id: int,
    data: StaffActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not data.new_stage_id:
        raise HTTPException(status_code=400, detail="new_stage_id is required")
    entry, err = visitor_flow.reassign_stage(
        db, entry_id, data.new_stage_id, user, data.reason
    )
    if err != "OK":
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "entry": queue_entry_to_dict(entry)}
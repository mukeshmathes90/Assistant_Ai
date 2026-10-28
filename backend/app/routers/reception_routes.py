"""Receptionist routes: visitor registration, search, queues, reassignment."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Department, Queue, QueueEntry, User, Visitor, WorkflowStage
from ..schemas import (
    VisitorCreateResponse,
    VisitorOut,
    VisitorRegisterIn,
)
from ..security import require_staff
from ..services.helpers import serialize_visitor
from ..services.qr_service import chat_base_url, qr_data_uri, visitor_chat_url
from ..services.queue_engine import stage_summary
from ..services.visitor_flow import register_visitor

router = APIRouter(prefix="/api/reception", tags=["Reception"])


@router.post("/visitors", response_model=VisitorCreateResponse)
def create_visitor(
    data: VisitorRegisterIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    visitor = register_visitor(
        db=db,
        full_name=data.full_name,
        phone=data.phone,
        purpose=data.purpose,
        department_id=data.department_id,
        remarks=data.remarks,
        needs_help_desk=data.needs_help_desk,
        registered_by=user,
    )
    out = serialize_visitor(db, visitor)
    response = VisitorCreateResponse(**out.model_dump())
    response.welcome_message = (
        f"Registered. Visitor ID {visitor.visitor_code} placed in the "
        f"'{visitor.current_stage.name}' queue."
        if visitor.current_stage
        else "Registration could not be completed."
    )
    return response


@router.get("/departments")
def list_departments(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return [
        {"id": d.id, "code": d.code, "name": d.name}
        for d in db.query(Department)
        .filter(Department.is_active.is_(True))
        .order_by(Department.name)
        .all()
    ]


@router.get("/visitors", response_model=list[VisitorOut])
def list_visitors(
    q: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    query = db.query(Visitor)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Visitor.full_name.ilike(like),
                Visitor.visitor_code.ilike(like),
                Visitor.phone.ilike(like),
            )
        )
    if status:
        query = query.filter(Visitor.status == status)
    visitors = query.order_by(Visitor.id.desc()).limit(50).all()
    return [serialize_visitor(db, v) for v in visitors]


@router.get("/visitors/active", response_model=list[VisitorOut])
def active_visitors(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    visitors = (
        db.query(Visitor)
        .filter(Visitor.status == "ACTIVE")
        .order_by(Visitor.id.desc())
        .limit(50)
        .all()
    )
    return [serialize_visitor(db, v) for v in visitors]


@router.get("/visitors/{visitor_id}", response_model=VisitorOut)
def get_visitor(
    visitor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    v = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return serialize_visitor(db, v)


@router.get("/visitors/{visitor_id}/qr")
def visitor_qr(
    visitor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """QR code that opens this visitor's AI chat + live queue tracker."""
    v = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    url = visitor_chat_url(v.phone)
    return {
        "visitor_code": v.visitor_code,
        "full_name": v.full_name,
        "phone": v.phone,
        "chat_url": url,
        "qr": qr_data_uri(url),
    }


@router.get("/chat-qr")
def desk_chat_qr(
    phone: str = "",
    user: User = Depends(require_staff),
):
    """General desk QR: opens the chat (optionally bound to a phone)."""
    url = visitor_chat_url(phone) if phone else f"{chat_base_url()}/chat"
    return {"chat_url": url, "qr": qr_data_uri(url)}


@router.get("/queues")
def list_queues(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    from ..models import QueueEntry as QE
    from ..services.helpers import queue_entry_to_dict

    stages = (
        db.query(WorkflowStage)
        .join(Queue, Queue.workflow_stage_id == WorkflowStage.id)
        .filter(WorkflowStage.is_active.is_(True))
        .order_by(WorkflowStage.workflow_id, WorkflowStage.stage_order)
        .all()
    )
    result = []
    for s in stages:
        summary = stage_summary(db, s)
        entries = (
            db.query(QE)
            .filter(
                QE.queue_id == summary["queue_id"],
                QE.status.in_(["WAITING", "CALLED", "SERVING", "HOLD"]),
            )
            .order_by(QE.position_order.asc())
            .all()
        )
        summary["entries"] = [queue_entry_to_dict(e) for e in entries]
        result.append(summary)
    return result


@router.get("/stage-map")
def stage_map(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """All active stages grouped by workflow (used for reassignment targets)."""
    stages = (
        db.query(WorkflowStage)
        .filter(WorkflowStage.is_active.is_(True))
        .order_by(WorkflowStage.workflow_id, WorkflowStage.stage_order)
        .all()
    )
    out = []
    for s in stages:
        out.append(
            {
                "id": s.id,
                "name": s.name,
                "queue_code": s.queue_code,
                "workflow_id": s.workflow_id,
                "workflow_name": s.workflow.name,
                "department_name": s.workflow.department.name
                if s.workflow and s.workflow.department
                else "Help Desk / General",
                "room_code": s.room.code if s.room else None,
            }
        )
    return out


@router.delete("/visitors/{visitor_id}")
def cancel_visitor(
    visitor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    v = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if v is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    v.status = "CANCELLED"
    for e in v.queue_entries:
        if e.status in ("WAITING", "CALLED", "SERVING", "HOLD"):
            e.status = "CANCELLED"
    db.commit()
    return {"ok": True, "visitor_code": v.visitor_code}
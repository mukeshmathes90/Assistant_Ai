"""Admin routes: configuration + statistics."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CollegeInformation,
    Department,
    FAQ,
    Queue,
    QueueEntry,
    Room,
    Staff,
    User,
    Visitor,
    VisitorStageHistory,
    Workflow,
    WorkflowStage,
)
from ..schemas import (
    CollegeInfoIn,
    CollegeInfoOut,
    DepartmentIn,
    DepartmentOut,
    FAQIn,
    FAQOut,
    RoomIn,
    RoomOut,
    StaffIn,
    StaffOut,
    StatsOut,
    UserOut,
    WorkflowIn,
    WorkflowOut,
)
from ..security import hash_password, require_roles
from ..services.helpers import serialize_visitor
from ..services.visitor_flow import reassign_stage

router = APIRouter(prefix="/api/admin", tags=["Admin"])
admin_only = require_roles("ADMIN")


# ---------------- Stats ----------------
@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    today0 = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    waiting = (
        db.query(QueueEntry)
        .filter(QueueEntry.status == "WAITING")
        .count()
    )
    serving = (
        db.query(QueueEntry)
        .filter(QueueEntry.status.in_(["CALLED", "SERVING"]))
        .count()
    )
    total_today = (
        db.query(Visitor).filter(Visitor.created_at >= today0).count()
    )
    completed_today = (
        db.query(Visitor)
        .filter(Visitor.completed_at >= today0)
        .filter(Visitor.status == "COMPLETED")
        .count()
    )
    active = (
        db.query(Visitor).filter(Visitor.status == "ACTIVE").count()
    )

    avg = 0
    done = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.status == "COMPLETED",
            QueueEntry.created_at >= today0,
        )
        .all()
    )
    if done:
        waits = [
            (e.completed_at - e.created_at).total_seconds() / 60.0
            for e in done
            if e.completed_at
        ]
        if waits:
            avg = int(sum(waits) / len(waits))

    by_dept = []
    for dept in db.query(Department).all():
        cnt = (
            db.query(Visitor)
            .filter(Visitor.department_id == dept.id)
            .filter(Visitor.created_at >= today0)
            .count()
        )
        if cnt:
            by_dept.append({"department": dept.code, "count": cnt})

    no_dept = (
        db.query(Visitor)
        .filter(Visitor.department_id.is_(None))
        .filter(Visitor.created_at >= today0)
        .count()
    )
    if no_dept:
        by_dept.append({"department": "HELP", "count": no_dept})

    return StatsOut(
        total_visitors_today=total_today,
        waiting=waiting,
        serving=serving,
        completed_today=completed_today,
        active_visitors=active,
        avg_wait_minutes=avg,
        by_department=by_dept,
        pending_stage_visitors=(
            db.query(VisitorStageHistory)
            .filter(VisitorStageHistory.status == "PENDING")
            .count()
        ),
    )


# ---------------- Departments ----------------
@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db), _: User = Depends(admin_only)
):
    return db.query(Department).order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentOut)
def create_department(
    data: DepartmentIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    if db.query(Department).filter(Department.code == data.code).first():
        raise HTTPException(status_code=400, detail="Department code already exists")
    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    data: DepartmentIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if dept is None:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump().items():
        setattr(dept, k, v)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}")
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if dept is None:
        raise HTTPException(status_code=404, detail="Not found")
    dept.is_active = False
    db.commit()
    return {"ok": True}


# ---------------- Rooms ----------------
@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.query(Room).order_by(Room.code).all()


@router.post("/rooms", response_model=RoomOut)
def create_room(
    data: RoomIn, db: Session = Depends(get_db), _: User = Depends(admin_only)
):
    room = Room(**data.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    data: RoomIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump().items():
        setattr(room, k, v)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/rooms/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Not found")
    room.is_active = False
    db.commit()
    return {"ok": True}


# ---------------- Staff / Users ----------------
@router.get("/staff", response_model=list[StaffOut])
def list_staff(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    result = []
    for s in db.query(Staff).order_by(Staff.id).all():
        dept = db.query(Department).filter(Department.id == s.department_id).first()
        result.append(
            StaffOut(
                id=s.id,
                employee_code=s.employee_code,
                designation=s.designation,
                user_id=s.user_id,
                username=s.user.username,
                full_name=s.user.full_name,
                phone=s.user.phone or "",
                department_id=s.department_id,
                department_code=dept.code if dept else None,
                is_active=s.is_active,
                assigned_stages=[
                    {
                        "id": st.id,
                        "name": st.name,
                        "stage_order": st.stage_order,
                        "queue_code": st.queue_code,
                        "is_active": st.is_active,
                    }
                    for st in s.assigned_stages
                ],
            )
        )
    return result


class StaffCreateIn(StaffIn):
    username: str
    password: str
    full_name: str
    phone: str = ""


@router.post("/staff", response_model=StaffOut)
def create_staff(
    data: StaffCreateIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role="STAFF",
    )
    db.add(user)
    db.flush()
    staff = Staff(
        user_id=user.id,
        employee_code=data.employee_code,
        designation=data.designation,
        department_id=data.department_id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return StaffOut(
        id=staff.id,
        employee_code=staff.employee_code,
        designation=staff.designation,
        user_id=staff.user_id,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone or "",
        department_id=staff.department_id,
        is_active=staff.is_active,
    )


@router.delete("/staff/{staff_id}")
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if staff is None:
        raise HTTPException(status_code=404, detail="Not found")
    staff.user.is_active = False
    staff.is_active = False
    db.commit()
    return {"ok": True}


# ---------------- Workflows ----------------
@router.get("/workflows", response_model=list[WorkflowOut])
def list_workflows(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return _workflow_list(db)


def _workflow_list(db):
    out = []
    for wf in db.query(Workflow).order_by(Workflow.id).all():
        dept = db.query(Department).filter(Department.id == wf.department_id).first()
        stages = []
        for st in sorted(wf.stages, key=lambda x: x.stage_order):
            stages.append(
                {
                    "id": st.id,
                    "name": st.name,
                    "stage_order": st.stage_order,
                    "queue_code": st.queue_code,
                    "room_id": st.room_id,
                    "room_name": st.room.name if st.room else None,
                    "staff_id": st.staff_id,
                    "staff_name": st.assigned_staff.user.full_name
                    if st.assigned_staff
                    else None,
                    "description": st.description,
                    "is_active": st.is_active,
                }
            )
        out.append(
            WorkflowOut(
                id=wf.id,
                code=wf.code,
                name=wf.name,
                department_id=wf.department_id,
                department_name=dept.name if dept else None,
                description=wf.description,
                is_active=wf.is_active,
                stages=stages,
            )
        )
    return out


# ---------------- Workflows ----------------
@router.post("/workflows", response_model=WorkflowOut)
def create_workflow(
    data: WorkflowIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    if db.query(Workflow).filter(Workflow.code == data.code).first():
        raise HTTPException(status_code=400, detail="Workflow code exists")
    wf = Workflow(**data.model_dump())
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _workflow_list(db)[-1]


@router.put("/workflows/{wf_id}", response_model=WorkflowOut)
def update_workflow(
    wf_id: int,
    data: WorkflowIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if wf is None:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump().items():
        setattr(wf, k, v)
    db.commit()
    for out in _workflow_list(db):
        if out.id == wf_id:
            return out
    raise HTTPException(status_code=404)


@router.delete("/workflows/{wf_id}")
def delete_workflow(
    wf_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if wf is None:
        raise HTTPException(status_code=404, detail="Not found")
    wf.is_active = False
    db.commit()
    return {"ok": True}


@router.post("/workflows/{wf_id}/stages")
def add_stage(
    wf_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    from ..schemas import WorkflowStageIn

    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    payload = WorkflowStageIn(**data)
    if payload.stage_order == 0:
        next_order = (
            (db.query(WorkflowStage.stage_order)
             .filter(WorkflowStage.workflow_id == wf_id)
             .order_by(WorkflowStage.stage_order.desc()).first()) or (0,)
        )[0] + 1
        payload.stage_order = next_order
    stage = WorkflowStage(
        workflow_id=wf_id,
        name=payload.name,
        stage_order=payload.stage_order,
        queue_code=payload.queue_code,
        room_id=payload.room_id,
        staff_id=payload.staff_id,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(stage)
    db.commit()
    # create its queue automatically
    queue = Queue(
        workflow_stage_id=stage.id, name=f"{stage.name} Queue"
    )
    db.add(queue)
    db.commit()
    return _workflow_list(db)


@router.put("/workflows/stages/{stage_id}")
def update_stage(
    stage_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    stage = db.query(WorkflowStage).filter(WorkflowStage.id == stage_id).first()
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    for k in ("name", "stage_order", "queue_code", "description", "is_active"):
        if k in data:
            setattr(stage, k, data[k])
    for k in ("room_id", "staff_id"):
        if k in data:
            setattr(stage, k, data[k])
    db.commit()
    return _workflow_list(db)


@router.delete("/workflows/stages/{stage_id}")
def delete_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    stage = db.query(WorkflowStage).filter(WorkflowStage.id == stage_id).first()
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    stage.is_active = False
    db.commit()
    return {"ok": True}


# ---------------- FAQs / Knowledge base ----------------
@router.get("/faqs", response_model=list[FAQOut])
def list_faqs(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.query(FAQ).order_by(FAQ.category, FAQ.id).all()


@router.post("/faqs", response_model=FAQOut)
def create_faq(
    data: FAQIn, db: Session = Depends(get_db), _: User = Depends(admin_only)
):
    faq = FAQ(**data.model_dump())
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return faq


@router.put("/faqs/{faq_id}", response_model=FAQOut)
def update_faq(
    faq_id: int,
    data: FAQIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if faq is None:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump().items():
        setattr(faq, k, v)
    db.commit()
    db.refresh(faq)
    return faq


@router.delete("/faqs/{faq_id}")
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if faq is None:
        raise HTTPException(status_code=404, detail="Not found")
    faq.is_active = False
    db.commit()
    return {"ok": True}


@router.get("/college-info", response_model=list[CollegeInfoOut])
def list_college_info(
    db: Session = Depends(get_db), _: User = Depends(admin_only)
):
    return db.query(CollegeInformation).order_by(CollegeInformation.category).all()


@router.post("/college-info", response_model=CollegeInfoOut)
def create_college_info(
    data: CollegeInfoIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    info = CollegeInformation(**data.model_dump())
    db.add(info)
    db.commit()
    db.refresh(info)
    return info


@router.put("/college-info/{info_id}", response_model=CollegeInfoOut)
def update_college_info(
    info_id: int,
    data: CollegeInfoIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    info = db.query(CollegeInformation).filter(CollegeInformation.id == info_id).first()
    if info is None:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump().items():
        setattr(info, k, v)
    db.commit()
    db.refresh(info)
    return info


@router.delete("/college-info/{info_id}")
def delete_college_info(
    info_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    info = db.query(CollegeInformation).filter(CollegeInformation.id == info_id).first()
    if info is None:
        raise HTTPException(status_code=404, detail="Not found")
    info.is_active = False
    db.commit()
    return {"ok": True}


# ---------------- Visitors (admin) ----------------
@router.get("/visitors")
def admin_visitors(
    q: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    from sqlalchemy import or_

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
    visitors = query.order_by(Visitor.id.desc()).limit(100).all()
    return [serialize_visitor(db, v) for v in visitors]


@router.post("/visitors/reassign/{visitor_id}")
def admin_reassign(
    visitor_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    """Reassign a visitor to a target stage (admin convenience)."""
    entry = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.visitor_id == visitor_id,
            QueueEntry.status.in_(["WAITING", "CALLED", "SERVING", "HOLD"]),
        )
        .order_by(QueueEntry.id.desc())
        .first()
    )
    if entry is None:
        raise HTTPException(status_code=400, detail="Visitor has no active queue entry")
    new_stage_id = data.get("new_stage_id")
    if not new_stage_id:
        raise HTTPException(status_code=400, detail="new_stage_id required")
    entry, err = reassign_stage(db, entry.id, int(new_stage_id), _admin_user(db))
    if err != "OK":
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True}


def _admin_user(db):
    return (
        db.query(User)
        .filter(User.role == "ADMIN")
        .first()
    )
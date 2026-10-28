"""Pydantic schemas (request/response models)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    phone: str = ""

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Department ----------
class DepartmentIn(BaseModel):
    code: str
    name: str
    description: str = ""
    is_active: bool = True


class DepartmentOut(DepartmentIn):
    id: int

    class Config:
        from_attributes = True


# ---------- Room ----------
class RoomIn(BaseModel):
    code: str
    name: str
    building: str = "Main Building"
    floor: str = "Ground Floor"
    counter: str = ""
    description: str = ""
    is_active: bool = True


class RoomOut(RoomIn):
    id: int

    class Config:
        from_attributes = True


# ---------- Staff ----------
class StaffIn(BaseModel):
    user_id: int
    employee_code: str
    designation: str = ""
    department_id: Optional[int] = None
    is_active: bool = True


class StaffStageOut(BaseModel):
    id: int
    name: str
    stage_order: int
    queue_code: str
    is_active: bool

    class Config:
        from_attributes = True


class StaffOut(BaseModel):
    id: int
    employee_code: str
    designation: str = ""
    user_id: int
    username: str
    full_name: str
    phone: str = ""
    department_id: Optional[int] = None
    department_code: Optional[str] = None
    is_active: bool
    assigned_stages: List[StaffStageOut] = []

    class Config:
        from_attributes = True


# ---------- Workflow ----------
class WorkflowStageIn(BaseModel):
    name: str
    stage_order: int
    queue_code: str
    room_id: Optional[int] = None
    staff_id: Optional[int] = None
    description: str = ""
    is_active: bool = True


class WorkflowIn(BaseModel):
    code: str
    name: str
    department_id: Optional[int] = None
    description: str = ""
    is_active: bool = True


class WorkflowStageOut(BaseModel):
    id: int
    name: str
    stage_order: int
    queue_code: str
    room_id: Optional[int] = None
    staff_id: Optional[int] = None
    room_name: Optional[str] = None
    staff_name: Optional[str] = None
    description: str = ""
    is_active: bool

    class Config:
        from_attributes = True


class WorkflowOut(BaseModel):
    id: int
    code: str
    name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    description: str = ""
    is_active: bool
    stages: List[WorkflowStageOut] = []

    class Config:
        from_attributes = True


# ---------- Visitor ----------
class VisitorRegisterIn(BaseModel):
    full_name: str
    phone: str
    purpose: str = "Admission"
    department_id: Optional[int] = None
    remarks: str = ""
    needs_help_desk: bool = False


class QueueEntryBriefOut(BaseModel):
    id: int
    token_display: str
    status: str
    queue_name: str = ""
    queue_id: int = 0
    position: Optional[int] = None

    class Config:
        from_attributes = True


class VisitorOut(BaseModel):
    id: int
    visitor_code: str
    full_name: str
    phone: str
    purpose: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    remarks: str = ""
    status: str
    current_workflow_id: Optional[int] = None
    current_workflow_name: Optional[str] = None
    current_stage_id: Optional[int] = None
    current_stage_name: Optional[str] = None
    room_code: Optional[str] = None
    room_name: Optional[str] = None
    assigned_staff_name: Optional[str] = None
    current_queue_entry: Optional[QueueEntryBriefOut] = None
    next_stage_name: Optional[str] = None
    next_stage_room: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VisitorCreateResponse(VisitorOut):
    welcome_message: str = ""


# ---------- Queue ----------
class QueueEntryOut(BaseModel):
    id: int
    queue_id: int
    visitor_id: int
    visitor_code: str
    visitor_name: str
    phone: str
    token_display: str
    status: str
    position_order: int
    room_id: Optional[int] = None
    room_code: Optional[str] = None
    room_name: Optional[str] = None
    called_at: Optional[datetime] = None
    served_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    hold_reason: str = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QueueOut(BaseModel):
    id: int
    name: str
    workflow_stage_id: int
    stage_name: str
    is_active: bool
    waiting_count: int = 0
    serving: Optional[QueueEntryOut] = None
    entries: List[QueueEntryOut] = []

    class Config:
        from_attributes = True


class StaffActionRequest(BaseModel):
    reason: str = ""
    new_stage_id: Optional[int] = None  # used by REASSIGN


# ---------- Chat / AI ----------
class ChatSendIn(BaseModel):
    phone: str
    message: str


class ChatMessageOut(BaseModel):
    id: int
    sender: str
    message: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    visitor: Optional[VisitorOut] = None
    visitors: List[VisitorOut] = []
    messages: List[ChatMessageOut] = []


# ---------- Knowledge base ----------
class FAQIn(BaseModel):
    question: str
    answer: str
    category: str = "General"
    keywords: str = ""
    department_id: Optional[int] = None
    is_active: bool = True
    source_url: str = ""
    source_type: str = "official_website"
    last_updated: Optional[datetime] = None


class FAQOut(FAQIn):
    id: int

    class Config:
        from_attributes = True


class CollegeInfoIn(BaseModel):
    key: str
    title: str
    content: str
    category: str = "College"
    is_active: bool = True
    source_url: str = ""
    source_type: str = "official_website"
    last_updated: Optional[datetime] = None


class CollegeInfoOut(CollegeInfoIn):
    id: int

    class Config:
        from_attributes = True


# ---------- Notifications ----------
class NotificationOut(BaseModel):
    id: int
    visitor_id: int
    message: str
    ntype: str
    is_read: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Stats ----------
class StatsOut(BaseModel):
    total_visitors_today: int = 0
    waiting: int = 0
    serving: int = 0
    completed_today: int = 0
    active_visitors: int = 0
    avg_wait_minutes: int = 0
    by_department: List[dict] = []
    by_stage_status: dict = {}
    pending_stage_visitors: int = 0
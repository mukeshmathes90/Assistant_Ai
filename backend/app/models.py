"""SQLAlchemy models for the admission assistance & visitor queue system."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflows = relationship("Workflow", back_populates="department")
    staff = relationship("Staff", back_populates="department")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    building = Column(String(100), default="Main Building")
    floor = Column(String(50), default="Ground Floor")
    counter = Column(String(50), default="")
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), default="")
    role = Column(String(20), nullable=False)  # ADMIN | RECEPTIONIST | STAFF
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff_profile = relationship(
        "Staff", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    employee_code = Column(String(30), unique=True, nullable=False)
    designation = Column(String(100), default="")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="staff_profile")
    department = relationship("Department", back_populates="staff")
    assigned_stages = relationship("WorkflowStage", back_populates="assigned_staff")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="workflows")
    stages = relationship(
        "WorkflowStage",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStage.stage_order",
    )


class WorkflowStage(Base):
    __tablename__ = "workflow_stages"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(
        Integer, ForeignKey("workflows.id"), nullable=False, index=True
    )
    name = Column(String(120), nullable=False)
    stage_order = Column(Integer, nullable=False)
    queue_code = Column(String(30), nullable=False)  # token prefix e.g. "ECE-COUNS"
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow = relationship("Workflow", back_populates="stages")
    room = relationship("Room")
    assigned_staff = relationship("Staff", back_populates="assigned_stages")
    queue = relationship(
        "Queue",
        back_populates="stage",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Queue(Base):
    """One real digital queue per active workflow stage."""

    __tablename__ = "queues"

    id = Column(Integer, primary_key=True)
    workflow_stage_id = Column(
        Integer, ForeignKey("workflow_stages.id"), nullable=False, unique=True
    )
    name = Column(String(160), nullable=False)
    current_token_number = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    stage = relationship("WorkflowStage", back_populates="queue")
    entries = relationship(
        "QueueEntry",
        back_populates="queue",
        cascade="all, delete-orphan",
    )


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id = Column(Integer, primary_key=True)
    queue_id = Column(Integer, ForeignKey("queues.id"), nullable=False, index=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=False, index=True)
    token_number = Column(Integer, nullable=False)
    token_display = Column(String(50), nullable=False)  # e.g. ECE-COUNS-121
    status = Column(String(20), nullable=False, default="WAITING", index=True)
    # WAITING | CALLED | SERVING | COMPLETED | HOLD | SKIPPED | CANCELLED
    position_order = Column(Integer, default=0)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    served_by_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    actioned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hold_reason = Column(String(200), default="")
    called_at = Column(DateTime, nullable=True)
    served_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    queue = relationship("Queue", back_populates="entries")
    visitor = relationship(
        "Visitor",
        back_populates="queue_entries",
        foreign_keys=[visitor_id],
    )
    room = relationship("Room")
    served_by_staff = relationship("Staff")
    actioned_by = relationship("User")


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True)
    visitor_code = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    purpose = Column(String(100), nullable=False, default="Admission")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    remarks = Column(Text, default="")
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    # ACTIVE | IN_PROGRESS | COMPLETED | CANCELLED
    current_workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    current_stage_id = Column(
        Integer, ForeignKey("workflow_stages.id"), nullable=True
    )
    current_queue_entry_id = Column(
        Integer, ForeignKey("queue_entries.id"), nullable=True
    )
    registered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    department = relationship("Department")
    current_workflow = relationship("Workflow")
    current_stage = relationship("WorkflowStage")
    current_queue_entry = relationship(
        "QueueEntry",
        foreign_keys=[current_queue_entry_id],
        post_update=True,
    )
    registered_by = relationship("User")
    queue_entries = relationship(
        "QueueEntry",
        back_populates="visitor",
        foreign_keys="QueueEntry.visitor_id",
        cascade="all, delete-orphan",
    )
    stage_history = relationship(
        "VisitorStageHistory",
        back_populates="visitor",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification", back_populates="visitor", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="visitor", cascade="all, delete-orphan"
    )


class VisitorStageHistory(Base):
    __tablename__ = "visitor_stage_history"

    id = Column(Integer, primary_key=True)
    visitor_id = Column(
        Integer, ForeignKey("visitors.id"), nullable=False, index=True
    )
    workflow_stage_id = Column(
        Integer, ForeignKey("workflow_stages.id"), nullable=False
    )
    queue_entry_id = Column(Integer, ForeignKey("queue_entries.id"), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING | COMPLETED | SKIPPED
    entered_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    actioned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    visitor = relationship("Visitor", back_populates="stage_history")
    workflow_stage = relationship("WorkflowStage")
    actioned_by = relationship("User")


class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True)
    question = Column(String(300), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    keywords = Column(String(300), default="")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    # Provenance / source tracking for the official knowledge base.
    source_url = Column(String(300), default="")
    source_type = Column(String(40), default="official_website")
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department")


class CollegeInformation(Base):
    __tablename__ = "college_information"

    id = Column(Integer, primary_key=True)
    key = Column(String(60), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="College")
    is_active = Column(Boolean, default=True)
    # Provenance / source tracking for the official knowledge base.
    source_url = Column(String(300), default="")
    source_type = Column(String(40), default="official_website")
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    ntype = Column(String(30), default="INFO")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    visitor = relationship("Visitor", back_populates="notifications")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=False, index=True)
    sender = Column(String(10), nullable=False)  # USER | AI | SYSTEM
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    visitor = relationship("Visitor", back_populates="chat_messages")


class TelegramSession(Base):
    """Links a Telegram chat to a registered visitor.

    Lets the same AI assistant answer on Telegram and report live queue
    status for the linked visitor (created automatically on first contact).
    """

    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True)
    chat_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(120), default="")
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visitor = relationship("Visitor")

class WhatsAppMessage(Base):
    """Log of WhatsApp Cloud API traffic (inbound + outbound).

    ``wa_message_id`` is unique, so a webhook event Meta delivers twice is
    stored once and answered once. Delivery receipts update ``status``.
    """

    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True)
    wa_message_id = Column(String(128), unique=True, nullable=True, index=True)
    direction = Column(String(3), nullable=False)  # IN | OUT
    phone = Column(String(32), nullable=False, index=True)
    msg_type = Column(String(20), default="text")
    body = Column(Text, default="")
    # IN: RECEIVED | REPLIED | IGNORED | FAILED
    # OUT: SENT | DELIVERED | READ | FAILED
    status = Column(String(20), default="RECEIVED")
    error = Column(String(500), default="")
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visitor = relationship("Visitor")

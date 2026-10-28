"""Workflow engine - decides which stage a visitor must go to next."""
from sqlalchemy.orm import Session

from ..models import Visitor, Workflow, WorkflowStage


def find_workflow_for_visitor(
    db: Session, department_id, purpose: str, needs_help_desk: bool = False
):
    """
    Picks the right admission workflow.

    - Unknown department / help-desk requests -> General Help Desk workflow.
    - Otherwise -> the department's active Admission workflow.
    """
    purpose_l = (purpose or "").lower()

    if needs_help_desk or department_id is None:
        wf = _find_help_desk_workflow(db)
        if wf:
            return wf

    if department_id is not None:
        wf = (
            db.query(Workflow)
            .filter(
                Workflow.department_id == department_id,
                Workflow.is_active.is_(True),
            )
            .order_by(Workflow.id.asc())
            .first()
        )
        if wf:
            return wf

    # fallback to any general workflow
    return _find_help_desk_workflow(db)


def _find_help_desk_workflow(db: Session):
    wf = (
        db.query(Workflow)
        .filter(Workflow.department_id.is_(None), Workflow.is_active.is_(True))
        .order_by(Workflow.id.asc())
        .first()
    )
    if wf:
        return wf
    # last resort: first active workflow
    return db.query(Workflow).filter(Workflow.is_active.is_(True)).first()


def first_stage(db: Session, workflow: Workflow):
    return (
        db.query(WorkflowStage)
        .filter(
            WorkflowStage.workflow_id == workflow.id,
            WorkflowStage.is_active.is_(True),
        )
        .order_by(WorkflowStage.stage_order.asc())
        .first()
    )


def next_stage(db: Session, workflow: Workflow, current_stage: WorkflowStage):
    """The next active stage after the current one, or None if finished."""
    return (
        db.query(WorkflowStage)
        .filter(
            WorkflowStage.workflow_id == workflow.id,
            WorkflowStage.is_active.is_(True),
            WorkflowStage.stage_order > current_stage.stage_order,
        )
        .order_by(WorkflowStage.stage_order.asc())
        .first()
    )


def previous_stage(db: Session, workflow: Workflow, current_stage: WorkflowStage):
    return (
        db.query(WorkflowStage)
        .filter(
            WorkflowStage.workflow_id == workflow.id,
            WorkflowStage.is_active.is_(True),
            WorkflowStage.stage_order < current_stage.stage_order,
        )
        .order_by(WorkflowStage.stage_order.desc())
        .first()
    )


def is_visitor_complete(db: Session, visitor: Visitor) -> bool:
    """True when the visitor has no active stage/queue left."""
    from ..models import QueueEntry

    entry = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.visitor_id == visitor.id,
            QueueEntry.status.in_(["WAITING", "CALLED", "SERVING", "HOLD"]),
        )
        .first()
    )
    return entry is None
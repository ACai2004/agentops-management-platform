"""方案路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.models.plan import ModificationPlan
from app.services import optimization_service

router = APIRouter(prefix="/api/plans", tags=["optimization"])


class ApplyBody(BaseModel):
    approved_by: str = "admin"


@router.get("/{plan_id}")
def get_plan(plan_id: UUID, db: Session = Depends(get_db)):
    plan = db.get(ModificationPlan, plan_id)
    if not plan:
        raise KeyError(f"方案 {plan_id} 不存在")
    return dump(plan)


@router.post("/{plan_id}/apply")
def apply_plan(plan_id: UUID, body: ApplyBody, db: Session = Depends(get_db)):
    return dump(optimization_service.apply_plan(db, plan_id, approved_by=body.approved_by))


@router.post("/{plan_id}/reject")
def reject_plan(plan_id: UUID, db: Session = Depends(get_db)):
    return dump(optimization_service.reject_plan(db, plan_id))

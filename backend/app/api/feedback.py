"""反馈 → 优化触发路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.services import optimization_service

router = APIRouter(prefix="/api/feedbacks", tags=["feedback"])


@router.post("/{feedback_id}/optimize")
async def optimize(feedback_id: UUID, db: Session = Depends(get_db)):
    return dump(await optimization_service.generate_plan(db, feedback_id))

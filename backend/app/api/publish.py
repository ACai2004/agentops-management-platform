"""发布 / 回滚路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.services import publish_service

router = APIRouter(prefix="/api", tags=["publish"])


class PublishBody(BaseModel):
    approved_by: str = "admin"


class RollbackBody(BaseModel):
    target_version_id: UUID
    approved_by: str = "admin"


@router.post("/versions/{version_id}/publish")
def publish(version_id: UUID, body: PublishBody, db: Session = Depends(get_db)):
    return dump(publish_service.publish(db, version_id, approved_by=body.approved_by))


@router.post("/agents/{agent_id}/rollback")
def rollback(agent_id: UUID, body: RollbackBody, db: Session = Depends(get_db)):
    return dump(
        publish_service.rollback(db, agent_id, body.target_version_id, approved_by=body.approved_by)
    )

"""版本路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.services import agent_service

router = APIRouter(prefix="/api/versions", tags=["versions"])


class UpdateDraftBody(BaseModel):
    prompt: str | None = None
    workflow_config: dict | None = None
    capability_bindings: dict | None = None
    knowledge_bindings: list[str] | None = None
    model_settings: dict | None = None


@router.get("/{version_id}")
def get_version(version_id: UUID, db: Session = Depends(get_db)):
    v = agent_service.get_version(db, version_id)
    if not v:
        raise KeyError(f"版本 {version_id} 不存在")
    return dump(v)


@router.put("/{version_id}")
def update_draft(version_id: UUID, body: UpdateDraftBody, db: Session = Depends(get_db)):
    return dump(
        agent_service.update_draft(
            db,
            version_id,
            prompt=body.prompt,
            workflow_config=body.workflow_config,
            capability_bindings=body.capability_bindings,
            model_settings=body.model_settings,
        )
    )

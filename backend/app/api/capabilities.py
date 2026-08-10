"""能力库路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.services import capability_service

router = APIRouter(prefix="/api", tags=["capabilities"])


class CreateCapabilityBody(BaseModel):
    name: str
    description: str
    trigger: str | None = None
    behavior_instruction: str
    output_spec: str | None = None
    examples: list | None = None
    created_by: str = "admin"


class BindCapabilityBody(BaseModel):
    name: str
    params: dict | None = None


class SaveAsBody(BaseModel):
    name: str
    description: str | None = None
    created_by: str = "admin"


@router.get("/capabilities")
def list_capabilities(db: Session = Depends(get_db)):
    return [dump(c) for c in capability_service.list_capabilities(db)]


@router.post("/capabilities")
def create_capability(body: CreateCapabilityBody, db: Session = Depends(get_db)):
    return dump(
        capability_service.create_capability(
            db,
            name=body.name,
            description=body.description,
            trigger=body.trigger,
            behavior_instruction=body.behavior_instruction,
            output_spec=body.output_spec,
            examples=body.examples,
            created_by=body.created_by,
        )
    )


@router.post("/versions/{version_id}/capabilities")
def bind_capability(version_id: UUID, body: BindCapabilityBody, db: Session = Depends(get_db)):
    return dump(capability_service.bind_capability(db, version_id, body.name, body.params))


@router.post("/versions/{version_id}/capabilities/{name}/save-as")
def save_as_capability(
    version_id: UUID, name: str, body: SaveAsBody, db: Session = Depends(get_db)
):
    return dump(
        capability_service.save_as_capability(
            db, version_id, name, name=body.name, description=body.description, created_by=body.created_by
        )
    )

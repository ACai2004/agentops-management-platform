"""知识库路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.services import knowledge_service

router = APIRouter(prefix="/api", tags=["knowledge"])


class CreateKnowledgeBody(BaseModel):
    name: str
    kind: str
    content: str
    created_by: str = "admin"


class UpdateKnowledgeBody(BaseModel):
    content: str


class BindKnowledgeBody(BaseModel):
    name: str


@router.get("/knowledge")
def list_knowledges(db: Session = Depends(get_db)):
    return [dump(k) for k in knowledge_service.list_knowledges(db)]


@router.post("/knowledge")
def create_knowledge(body: CreateKnowledgeBody, db: Session = Depends(get_db)):
    return dump(
        knowledge_service.create_knowledge(
            db, name=body.name, kind=body.kind, content=body.content, created_by=body.created_by
        )
    )


@router.put("/knowledge/{name}")
def update_knowledge(name: str, body: UpdateKnowledgeBody, db: Session = Depends(get_db)):
    return dump(knowledge_service.update_knowledge(db, name, content=body.content))


@router.post("/versions/{version_id}/knowledge")
def bind_knowledge(version_id: UUID, body: BindKnowledgeBody, db: Session = Depends(get_db)):
    return dump(knowledge_service.bind_knowledge(db, version_id, body.name))


@router.delete("/versions/{version_id}/knowledge/{name}")
def unbind_knowledge(version_id: UUID, name: str, db: Session = Depends(get_db)):
    return dump(knowledge_service.unbind_knowledge(db, version_id, name))

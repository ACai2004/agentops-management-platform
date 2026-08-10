"""Agent 路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.models.agent import Agent, AgentVersion
from app.services import agent_service

router = APIRouter(prefix="/api/agents", tags=["agents"])


class CreateAgentBody(BaseModel):
    name: str
    description: str | None = None


@router.post("")
def create_agent(body: CreateAgentBody, db: Session = Depends(get_db)):
    return dump(agent_service.create_agent(db, name=body.name, description=body.description))


@router.get("")
def list_agents(db: Session = Depends(get_db)):
    return [dump(a) for a in db.scalars(select(Agent).order_by(Agent.created_at.desc())).all()]


@router.get("/{agent_id}")
def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise KeyError(f"Agent {agent_id} 不存在")
    data = dump(agent)
    data["current_version"] = dump(db.get(AgentVersion, agent.current_version_id)) if agent.current_version_id else None
    return data


@router.get("/{agent_id}/versions")
def list_versions(agent_id: UUID, db: Session = Depends(get_db)):
    return [dump(v) for v in agent_service.list_versions(db, agent_id)]


@router.post("/{agent_id}/versions")
def create_draft(agent_id: UUID, db: Session = Depends(get_db)):
    return dump(agent_service.create_draft(db, agent_id))

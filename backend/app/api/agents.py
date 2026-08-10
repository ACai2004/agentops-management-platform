"""Agent 路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.models.agent import AgentVersion
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
    return [dump(a) for a in agent_service.list_agents(db)]


@router.get("/{agent_id}")
def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    agent = agent_service.get_agent(db, agent_id)
    if not agent:
        raise KeyError(f"Agent {agent_id} 不存在")
    data = dump(agent)
    data["current_version"] = (
        dump(db.get(AgentVersion, agent.current_version_id)) if agent.current_version_id else None
    )
    return data


@router.delete("/{agent_id}")
def delete_agent(agent_id: UUID, db: Session = Depends(get_db)):
    """软删除 Agent（历史数据保留，从列表隐藏）。"""
    agent_service.delete_agent(db, agent_id)
    return {"deleted": str(agent_id)}


@router.get("/{agent_id}/versions")
def list_versions(agent_id: UUID, db: Session = Depends(get_db)):
    return [dump(v) for v in agent_service.list_versions(db, agent_id)]


@router.post("/{agent_id}/versions")
def create_draft(agent_id: UUID, db: Session = Depends(get_db)):
    return dump(agent_service.create_draft(db, agent_id))

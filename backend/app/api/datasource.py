"""数据源路由（§11）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.services import datasource_service

router = APIRouter(prefix="/api/datasources", tags=["datasources"])


class CreateDatasourceBody(BaseModel):
    name: str
    base_url: str
    method: str = "GET"
    headers: dict | None = None
    kind: str | None = None
    created_by: str = "admin"


class UpdateDatasourceBody(BaseModel):
    base_url: str | None = None
    method: str | None = None
    headers: dict | None = None
    kind: str | None = None


@router.get("")
def list_datasources(db: Session = Depends(get_db)):
    return [dump(d) for d in datasource_service.list_datasources(db)]


@router.post("")
def create_datasource(body: CreateDatasourceBody, db: Session = Depends(get_db)):
    return dump(
        datasource_service.create_datasource(
            db,
            name=body.name,
            base_url=body.base_url,
            method=body.method,
            headers=body.headers,
            kind=body.kind,
            created_by=body.created_by,
        )
    )


@router.put("/{name}")
def update_datasource(name: str, body: UpdateDatasourceBody, db: Session = Depends(get_db)):
    return dump(
        datasource_service.update_datasource(
            db,
            name,
            base_url=body.base_url,
            method=body.method,
            headers=body.headers,
            kind=body.kind,
        )
    )


@router.delete("/{name}")
def delete_datasource(name: str, db: Session = Depends(get_db)):
    datasource_service.delete_datasource(db, name)
    return {"deleted": name}

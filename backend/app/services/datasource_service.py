"""DatasourceService：数据源 CRUD（§10.7）。

数据源是外部 API 连接配置（base_url / method / headers，含 key），供 http 节点按名引用。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.datasource import Datasource


def create_datasource(
    db: Session,
    *,
    name: str,
    base_url: str,
    method: str = "GET",
    headers: dict | None = None,
    kind: str | None = None,
    created_by: str = "admin",
) -> Datasource:
    ds = Datasource(
        name=name,
        base_url=base_url,
        method=method,
        headers=headers or {},
        kind=kind,
        created_by=created_by,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def list_datasources(db: Session) -> list[Datasource]:
    return list(db.scalars(select(Datasource).order_by(Datasource.name)))


def get_datasource(db: Session, name: str) -> Datasource | None:
    return db.scalar(select(Datasource).where(Datasource.name == name))


def update_datasource(
    db: Session,
    name: str,
    *,
    base_url: str | None = None,
    method: str | None = None,
    headers: dict | None = None,
    kind: str | None = None,
) -> Datasource:
    ds = get_datasource(db, name)
    if not ds:
        raise KeyError(f"数据源 {name} 不存在")
    if base_url is not None:
        ds.base_url = base_url
    if method is not None:
        ds.method = method
    if headers is not None:
        ds.headers = headers
    if kind is not None:
        ds.kind = kind
    db.commit()
    db.refresh(ds)
    return ds


def delete_datasource(db: Session, name: str) -> None:
    ds = get_datasource(db, name)
    if not ds:
        raise KeyError(f"数据源 {name} 不存在")
    db.delete(ds)
    db.commit()

"""DatasourceService：数据源 CRUD（§10.7）。

数据源是外部 API 连接配置（base_url / method / headers，含 key），供 http 节点按名引用。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contracts import DatasourceParam
from app.models.datasource import Datasource


def validate_param_defs(param_defs: list | None) -> list[dict]:
    """校验参数契约：名字非空/不重复；select 必须配选项。返回规范化的 dict 列表。"""
    out: list[dict] = []
    seen: set[str] = set()
    for p in param_defs or []:
        d = DatasourceParam.model_validate(p)
        if not d.name.strip():
            raise ValueError("参数定义：参数名不能为空")
        if d.name in seen:
            raise ValueError(f"参数定义：参数名重复：{d.name}")
        if d.type == "select" and not d.options:
            raise ValueError(f"参数定义：{d.name} 是下拉类型但未配置选项")
        seen.add(d.name)
        out.append(d.model_dump())
    return out


def create_datasource(
    db: Session,
    *,
    name: str,
    base_url: str,
    method: str = "GET",
    headers: dict | None = None,
    param_defs: list | None = None,
    kind: str | None = None,
    created_by: str = "admin",
) -> Datasource:
    ds = Datasource(
        name=name,
        base_url=base_url,
        method=method,
        headers=headers or {},
        param_defs=validate_param_defs(param_defs),
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
    param_defs: list | None = None,
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
    if param_defs is not None:
        ds.param_defs = validate_param_defs(param_defs)
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

"""API 路由层（§11）。"""


def dump(obj):
    """SQLAlchemy 对象 → dict（FastAPI 可直接序列化；datetime/JSONB 由 FastAPI 编码）。"""
    if obj is None:
        return None
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}

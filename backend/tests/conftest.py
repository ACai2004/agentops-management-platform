"""pytest fixtures：独立的测试数据库（agentops_test），与开发库隔离，测试结束清理。

仅当测试请求 db_session 时才创建测试库；纯单元测试（契约/运行时等）不触发。
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.db import Base

_TEST_DB = "agentops_test"


def _test_url(database: str):
    return make_url(settings.database_url).set(database=database)


@pytest.fixture(scope="session")
def test_engine():
    """创建独立的 agentops_test 库，用 Base.metadata 建表；会话结束删除。"""
    admin = create_engine(_test_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {_TEST_DB}"))
        conn.execute(text(f"CREATE DATABASE {_TEST_DB}"))
    admin.dispose()

    engine = create_engine(_test_url(_TEST_DB))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

    admin = create_engine(_test_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {_TEST_DB}"))
    admin.dispose()


@pytest.fixture()
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

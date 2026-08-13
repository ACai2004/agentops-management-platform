"""数据源参数契约（param_defs）校验测试。"""

import pytest

from app.services import datasource_service


def test_create_datasource_with_param_defs(db_session):
    ds = datasource_service.create_datasource(
        db_session,
        name="高德天气2",
        base_url="https://restapi.amap.com/v3/weather/weatherInfo",
        param_defs=[
            {"name": "city", "label": "城市编码", "required": True, "type": "text"},
            {"name": "extensions", "label": "预报/实时", "type": "select", "options": ["base", "all"]},
        ],
    )
    assert ds.param_defs[0]["name"] == "city"
    assert ds.param_defs[0]["required"] is True
    assert ds.param_defs[1]["type"] == "select"


def test_param_defs_duplicate_name_rejected(db_session):
    with pytest.raises(ValueError, match="重复"):
        datasource_service.create_datasource(
            db_session,
            name="dup",
            base_url="https://x",
            param_defs=[
                {"name": "city", "type": "text"},
                {"name": "city", "type": "text"},
            ],
        )


def test_param_defs_empty_name_rejected(db_session):
    with pytest.raises(ValueError, match="不能为空"):
        datasource_service.create_datasource(
            db_session, name="empty", base_url="https://x", param_defs=[{"name": "", "type": "text"}]
        )


def test_param_defs_select_without_options_rejected(db_session):
    with pytest.raises(ValueError, match="未配置选项"):
        datasource_service.create_datasource(
            db_session, name="sel", base_url="https://x", param_defs=[{"name": "ext", "type": "select"}]
        )

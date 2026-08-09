"""模型能力登记表（蓝图 §5 / 《AgentOps工作流校验与运行时设计.md》§5）。

模型支持什么能力由它声明，不写死在节点里；加新模型 = 登记表加一行 + LiteLLM 路由加一个模型。
"""

from app.core.config import settings

# 能力登记表：主文本模型 + 视觉模型（经 OpenRouter，用户已验证支持图片）
MODEL_CAPABILITIES: dict[str, dict[str, bool]] = {
    "deepseek/deepseek-v4-flash": {"text": True, "vision": False, "audio": False, "json_mode": True},
    settings.vision_model: {"text": True, "vision": True, "audio": False, "json_mode": True},
}


def model_supports(model: str, required: list[str]) -> bool:
    """检查模型是否具备全部所需能力。

    未知模型默认视为支持（不误报），由运行时实际请求兜底；已知模型按登记表严格判断。
    """
    caps = MODEL_CAPABILITIES.get(model)
    if caps is None:
        return True
    return all(caps.get(c, False) for c in required)

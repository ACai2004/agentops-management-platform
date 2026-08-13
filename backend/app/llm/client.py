"""LiteLLM 网关（§8.1）。

统一 provider + 路由/故障转移：主用 DeepSeek，备用兜底。
业务代码统一走 call() / call_structured()，不直接碰 litellm。
"""

from litellm import Router

from app.core.config import settings

# 配置两个模型：主用 DeepSeek，备用兜底（可配 OpenAI 兼容任意 key）
router = Router(
    model_list=[
        {
            "model_name": "primary",
            "litellm_params": {
                "model": settings.llm_model,
                "api_key": settings.deepseek_api_key,
            },
        },
        {
            "model_name": "fallback",
            "litellm_params": {
                "model": settings.llm_model,
                "api_key": settings.backup_model_key or settings.deepseek_api_key,
            },
        },
        {
            "model_name": "vision",
            "litellm_params": {
                "model": settings.vision_model,
                "api_key": settings.openrouter_key,
            },
        },
    ],
    fallbacks=[{"primary": ["fallback"]}],   # 主模型失败/限流时切备用
    num_retries=2,
)


async def call(
    messages: list[dict],
    model: str = "primary",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    """调用 LLM 并返回文本内容。"""
    if json_mode:
        # DeepSeek 硬性要求：response_format=json_object 时 prompt 里必须出现 "json" 字样。
        # 判断分支等结构化调用如果提示词没写 json，自动补一句引导，避免 BadRequestError。
        text = " ".join(str(m.get("content", "")) for m in messages)
        if "json" not in text.lower():
            messages = [*messages]
            if messages and messages[-1]["role"] == "user" and isinstance(messages[-1]["content"], str):
                messages[-1] = {**messages[-1], "content": messages[-1]["content"] + "\n\n请严格按 JSON 格式输出。"}
            else:
                messages.append({"role": "user", "content": "请严格按 JSON 格式输出。"})
    resp = await router.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"} if json_mode else None,
    )
    return resp.choices[0].message.content

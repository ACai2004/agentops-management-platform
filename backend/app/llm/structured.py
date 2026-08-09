"""结构化输出通道（§8.2）—— 平台关键能力。

调用 LLM 并返回符合 pydantic schema 的对象；失败自动重试，
并把校验错误信息回喂给 LLM 再试。
"""

import json

from pydantic import BaseModel, ValidationError

from app.llm.client import call


class StructuredOutputError(Exception):
    """连续 max_retries 次仍无法通过 schema 校验。"""


async def call_structured(
    schema: type[BaseModel],
    system: str,
    user: str,
    max_retries: int = 3,
    model: str = "primary",
) -> BaseModel:
    """调用 LLM 并返回符合 schema 的 pydantic 对象；失败自动重试。"""
    for attempt in range(max_retries):
        raw = await call(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model=model,
            json_mode=True,
        )
        try:
            data = json.loads(raw)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            # 把错误信息回喂给 LLM 再试
            user = f"{user}\n\n上次输出无法通过校验：{e}\n请严格按 JSON schema 重新输出。"
    raise StructuredOutputError(f"{schema.__name__} 连续 {max_retries} 次校验失败")

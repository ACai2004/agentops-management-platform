"""结构化输出通道（§8.2）—— 平台关键能力。

调用 LLM 并返回符合 pydantic schema 的对象；失败自动重试，
并把校验错误信息回喂给 LLM 再试。
"""

import json

from pydantic import BaseModel, ValidationError

from app.llm.client import call


class StructuredOutputError(Exception):
    """连续 max_retries 次仍无法通过 schema 校验。"""


def _extract_json(raw: str) -> str:
    """剥离模型可能加上的 markdown 代码围栏（```json ... ```），返回纯 JSON。"""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


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
            max_tokens=4096,  # 结构化输出 JSON 较长，防止被截断
        )
        try:
            data = json.loads(_extract_json(raw))
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            # 把错误信息回喂给 LLM 再试
            user = f"{user}\n\n上次输出无法通过校验：{e}\n请严格按 JSON schema 重新输出。"
    raise StructuredOutputError(f"{schema.__name__} 连续 {max_retries} 次校验失败")

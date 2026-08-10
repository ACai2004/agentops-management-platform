"""LLM 结构化输出的 schema（§8.2）。

- DecisionOutput：decision 节点的分支判断
- Change / ModificationPlan：AI 优化助手返回的可应用修改方案
"""

import re
from typing import Literal

from pydantic import BaseModel, field_validator


class DecisionOutput(BaseModel):
    choice: str                     # decision 节点的分支值


class Change(BaseModel):
    target: Literal["prompt", "workflow", "model_settings", "capability_bindings"]
    operation: Literal["replace", "add_node", "update_node", "remove_node", "add", "remove"]
    path: str | None = None         # 如 "steps.satisfaction_check" / "prompt"
    value: dict | str | None = None # 新值（节点定义/新 prompt 等）
    description: str                # 给业务人员看的人类可读说明


class ModificationPlan(BaseModel):
    problem_analysis: str           # 问题是什么
    root_cause: str                 # 为什么产生
    suggestions: list[str]          # 建议摘要（展示）
    changes: list[Change]           # 可被 backend 直接应用的变更列表

    @field_validator("suggestions", mode="before")
    @classmethod
    def _coerce_suggestions(cls, v):
        """容错：模型偶发把 suggestions 返回成字符串（"1. ... 2. ..."），自动拆成数组。"""
        if isinstance(v, str):
            parts = re.split(r"[\n;]+", v)
            return [p.strip().lstrip("- ").strip() for p in parts if p.strip()]
        return v

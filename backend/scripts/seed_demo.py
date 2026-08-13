"""种子数据：餐后漫谈演示 Agent（蓝图 §14.2 / 测试场景二）。

幂等：共享资源（知识 / 数据源）已存在则复用，不重复创建；
Agent 每次运行新建一个「餐后漫谈助手（演示）」。

用法：
    cd backend
    conda run -n agentops python scripts/seed_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from app.core.config import settings  # noqa: E402
from app.services import (  # noqa: E402
    agent_service,
    datasource_service,
    knowledge_service,
    publish_service,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS = PROJECT_ROOT / "docs"


# ---------------------------------------------------------------------------
# 共享资源（幂等：存在即跳过）
# ---------------------------------------------------------------------------


def _ensure_knowledge(db, *, name: str, kind: str, content: str):
    if knowledge_service.get_knowledge(db, name):
        print(f"[知识] 已存在，跳过：{name}")
        return
    knowledge_service.create_knowledge(db, name=name, kind=kind, content=content, created_by="seed")
    print(f"[知识] 已创建：{name}（{len(content)} 字）")


def _menu_content() -> str:
    """从 sample-dish-knowledge.json 格式化「餐厅菜单」知识（每道菜一行）。"""
    dishes = json.loads((DOCS / "sample-dish-knowledge.json").read_text(encoding="utf-8"))
    lines = ["餐厅菜品知识库（名称/角色/特点/体验方向），用于小票识别匹配与体验推测："]
    for d in dishes:
        role = d.get("dishRole", "")
        features = "、".join(d.get("features", []) or [])
        tags = "、".join(d.get("experienceTags", []) or [])
        lines.append(f"- {d['dishName']}（{role}）：{features}；体验方向：{tags}")
    return "\n".join(lines)


def _environment_content() -> str:
    r = json.loads((DOCS / "sample-restaurants.json").read_text(encoding="utf-8"))
    env = "、".join(r.get("environmentFeatures", []))
    svc = "、".join(r.get("serviceFeatures", []))
    tags = "、".join(r.get("experienceTags", []))
    sig = "、".join(r.get("signatureDishes", []))
    return (
        f"餐厅：{r.get('restaurantName')}（{r.get('address')}）\n"
        f"定位：{r.get('positioning')}\n"
        f"环境：{env}\n服务：{svc}\n"
        f"体验标签：{tags}\n招牌菜：{sig}"
    )


def _profile_content() -> str:
    p = json.loads((DOCS / "user-profile.json").read_text(encoding="utf-8"))
    basic = p.get("basicInfo", {})
    return (
        f"用户：{basic.get('gender', '')} {basic.get('ageRange', '')}岁，{basic.get('city', '')}\n"
        f"口味偏好：{p.get('tastePreference', '')}\n"
        f"喜爱菜系：{', '.join(p.get('diningBehavior', {}).get('favoriteCuisine', []))}\n"
        f"场景偏好：{', '.join(p.get('scenePreference', {}).get('occasion', []))}"
    )


def _ensure_datasource(db):
    param_defs = [
        {
            "name": "city",
            "label": "城市编码",
            "required": True,
            "type": "text",
            "placeholder": "如 110105 或 {{adcode}}",
        },
        {"name": "extensions", "label": "预报/实时", "required": False, "type": "select", "options": ["base", "all"]},
    ]
    existing = datasource_service.get_datasource(db, "高德天气")
    if existing:
        # 幂等：补全参数契约（地址/key 不动）
        if existing.param_defs != param_defs:
            datasource_service.update_datasource(db, "高德天气", param_defs=param_defs)
        print("[数据源] 已存在，补全参数契约：高德天气")
        return
    # 无 key 占位：请在前端「数据源」页填入真实 key（或 base_url 自带 ?key=...）
    datasource_service.create_datasource(
        db,
        name="高德天气",
        base_url="https://restapi.amap.com/v3/weather/weatherInfo",
        method="GET",
        headers={},
        param_defs=param_defs,
        kind="weather",
        created_by="seed",
    )
    print("[数据源] 已创建：高德天气（请在前端补上 key）")


# ---------------------------------------------------------------------------
# 餐后漫谈演示 Agent
# ---------------------------------------------------------------------------


def _vision_prompt() -> str:
    """视觉识别节点 prompt：小票识别（修改版）——参考餐品列表引用绑定的菜单知识。

    视觉模型在识别时就做"菜品匹配"，只输出能匹配到菜单的菜品（菜名规范化为菜单标准名）。
    """
    return """你是餐厅消费小票识别助手。请从用户提供的图片中识别是否为餐厅消费小票，
并提取订单级信息（餐厅名、用餐时间、用餐人数、单号）和各餐品明细（名称、数量、备注、单价）。

## 参考餐品列表
以下是该门店当前上架的餐品（名称+描述），用于匹配小票上的餐品：
参考餐品列表见系统消息中的【知识库「餐厅菜单」】，只从其中匹配菜品。

**重要**：
- 识别到的餐品名称请优先使用参考列表中的标准名称
- 如果小票上的名称与参考名称略有差异（如简称、错字、漏字），匹配最接近的参考名称
- **无法匹配到参考列表的项，静默过滤，不要输出**

## 输出要求
请严格按以下 JSON 格式返回，不要包含任何其他文字：
{
  "isReceipt": true,
  "restaurant": "餐厅名",
  "time": "结账时间",
  "people": 人数,
  "items": [
    { "name": "打抛饭", "quantity": 1, "notes": "不可免辣，牛肉", "price": "38" }
  ]
}

## 字段说明
- `restaurant`：小票顶部的餐厅名称
- `time`：结账时间；`people`：小票打印的用餐人数（没有则不输出）
- `items`：仅输出匹配到参考餐品列表的项；`name` 用参考列表的标准名称
- `notes`：必须包含菜名括号里的修饰词（如"（不可免辣）"）以及备注区的规格/做法/辣度/加料
- `price`：单价（保留原样字符串）

## 规则
1. 先判断图片是否为餐厅消费小票（含餐品清单和金额）。若不是（风景/截图/手写/超市小票等），
   `isReceipt` 设为 false，`items` 为空数组
2. 仅输出能匹配到参考餐品列表的餐品（匹配不到的静默过滤）
3. 菜名括号里的修饰词必须提取到 `notes`，不能丢失
4. 若小票上没有明确餐品信息，返回 `items: []`（`isReceipt` 仍为 true）
5. 只返回 JSON，不要返回任何解释性文字"""


def _experience_prompt() -> str:
    """Experience Understanding（Layer 2）：Java 版 ExperienceUnderstandingAgent 原版 SystemMessage。

    把订单/菜品/实时环境转成体验可能性，低确定性、禁止当结论、结构化输出。
    """
    return """你是一个餐后体验分析专家。
根据订单信息、菜品知识和实时环境，
推测本次用餐可能存在的体验场景。

关键约束（必须遵守）：
1. 所有输出必须是「可能性」，不是「结论」
2. 必须保持低确定性
3. 禁止将推测当作事实
4. 每条可能性必须标注 confidenceLevel（只能是 LOW 或 MEDIUM，不允许 HIGH）
5. 如果信息不足以判断，输出空列表

输出 JSON 格式，根对象包含 possibilities 数组，每项包含：
- description（体验可能性描述）
- confidenceLevel（只能是 LOW 或 MEDIUM）
- evidenceSource（推测依据，如"订单显示 3 人用餐"）"""


def _planner_prompt() -> str:
    """Conversation Planner（Layer 3）：Java 版 ConversationPlannerAgent 原版 SystemMessage。

    根据订单/菜品/实时/体验理解，为 Voice Agent 生成对话策略（方向/机会点/限制）。
    """
    return """你是一个对话规划专家。
根据订单信息、菜品知识、实时信息以及体验理解分析，
为 Voice Agent 生成对话策略。

输出结构：
1. Directions（方向）：当前适合关注什么
2. Available Hooks（机会点）：可以自然利用的话题
3. Avoid（限制）：应避免的方向

重要约束（必须遵守）：
1. 不要输出聊天脚本（不要写"第一句话说什么，第二句话说什么"）
2. 不要指定具体的台词
3. 方向是框架性的，不是时间线顺序
4. Hooks 是自然切入点，不是待办清单
5. 根据菜品的 dishRole 决定交流参与程度：
   - SIGNATURE + MAIN：用户表现出兴趣时可以深入聊
   - STAPLE + DESSERT：自然流动时提及
   - SIDE + CONDIMENT：不主动提及，用户说到再跟
   - DRINK：普通饮品不提，特色饮品可一带而过

输出 JSON 格式，包含以下字段：
- directions（字符串数组）
- availableHooks（字符串数组）
- avoid（字符串数组）"""


def _runtime_prompt_template() -> str:
    """Prompt Assembly 模板：对应 Java 版 PromptAssembler（方案 B）。

    Runtime Prompt = Static System Prompt（system-prompt.md 原文内嵌）+ 分隔符 + Dynamic Context（三层）。
    纯函数拼接，不经过 LLM；{{var}} 注入前序产物。静态提示词只在这里被使用（不注入其他节点）。
    """
    static = (DOCS / "system-prompt.md").read_text(encoding="utf-8").strip()
    return (
        f"{static}\n"
        "\n"
        "---\n"
        "\n"
        "以下是用餐背景信息：\n"
        "\n"
        "【订单信息】\n"
        "{{order}}\n"
        "\n"
        "【实时信息】\n"
        "{{weather}}\n"
        "\n"
        "【体验理解】\n"
        "{{experience}}\n"
        "\n"
        "【对话规划】\n"
        "{{plan}}"
    )


def _build_workflow():
    return {
        "start": "order_understand",
        "inputs": [
            {"name": "receipt_image", "label": "小票照片", "type": "image", "required": True},
            {"name": "user_text", "label": "补充文本", "type": "text", "required": False},
        ],
        "steps": {
            "order_understand": {
                "type": "llm",
                "prompt": _vision_prompt(),
                "save_as": "order",
                "next": "fetch_weather",
                "image_input": True,
                "model_settings": {"model": settings.vision_model},
            },
            "fetch_weather": {
                "type": "http",
                "datasource": "高德天气",
                "params": {"city": "110105"},  # 朝阳区 adcode（三里屯）
                "save_as": "weather",
                "next": "experience",
            },
            "experience": {
                "type": "llm",
                "prompt": _experience_prompt(),
                "save_as": "experience",
                "next": "planner",
            },
            "planner": {
                "type": "llm",
                "prompt": _planner_prompt(),
                "save_as": "plan",
                "next": "assemble",
            },
            "assemble": {
                "type": "template",
                "template": _runtime_prompt_template(),
                "save_as": "output",
                "next": "end",
            },
            "end": {"type": "end"},
        },
    }


def main():
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        # 1) 共享资源
        _ensure_knowledge(db, name="餐厅菜单", kind="menu", content=_menu_content())
        _ensure_knowledge(db, name="餐厅环境", kind="environment", content=_environment_content())
        _ensure_knowledge(db, name="用户画像10001", kind="profile", content=_profile_content())
        _ensure_datasource(db)

        # 2) 餐后漫谈演示 Agent（先软删同名旧演示，避免堆积）
        for old in agent_service.list_agents(db):
            if old.name == "餐后漫谈助手（演示）" and not old.deleted_at:
                agent_service.delete_agent(db, old.id)
        agent = agent_service.create_agent(db, name="餐后漫谈助手（演示）", description="小票→菜品检索→天气→体验理解→对话规划→Runtime Prompt（复刻 Java 版）", created_by="seed")
        v1 = agent_service.list_versions(db, agent.id)[0]
        # 无全局提示词：system-prompt.md 只内嵌进模板节点做最终拼接，不注入其他节点
        v1 = agent_service.update_draft(
            db,
            v1.id,
            prompt="",
            workflow_config=_build_workflow(),
        )
        v1 = knowledge_service.bind_knowledge(db, v1.id, "餐厅菜单")
        v1 = knowledge_service.bind_knowledge(db, v1.id, "餐厅环境")
        v1 = publish_service.publish(db, v1.id, approved_by="seed")
        print(f"[Agent] 已创建并发布：餐后漫谈助手（演示）  id={agent.id}  V{v1.version_no}")
        print("  · 绑定知识：餐厅菜单、餐厅环境")
        print("  · 输入清单：小票照片（必填图片）、补充文本（可选）")
        print("  · 流程：订单理解(视觉+菜品匹配) → 天气(高德) → 体验理解 → 对话规划 → Prompt Assembly")
        print("  去前端「餐后漫谈助手（演示）」→ 测试页上传小票即可运行。")
    finally:
        db.close()


if __name__ == "__main__":
    main()

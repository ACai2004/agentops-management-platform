"""蓝图 §5.1 的示例 workflow_config（回访 Agent），供多个测试共享（Layer 9 种子数据同源）。"""

SAMPLE_WORKFLOW = {
    "start": "understanding",
    "steps": {
        "understanding": {
            "type": "llm",
            "prompt": "你是餐后体验回访助手。先理解用户反馈，然后回复。",
            "save_as": "understanding_reply",
            "next": "satisfaction_check",
        },
        "satisfaction_check": {
            "type": "decision",
            "prompt": '判断用户反馈的满意度，只输出 JSON：{"choice": "satisfied" | "neutral" | "unsatisfied"}',
            "save_as": "satisfaction",
            "branches": {
                "satisfied": "coupon_offer",
                "neutral": "problem_collection",
                "unsatisfied": "problem_collection",
            },
        },
        "coupon_offer": {
            "type": "llm",
            "prompt": "用户反馈满意。以自然口吻表达感谢，并告知近期有优惠活动。",
            "save_as": "output",
            "next": "end",
        },
        "problem_collection": {
            "type": "llm",
            "prompt": "用户反馈一般或不满意。用开放式问题引导用户说出具体不满，并记录关键信息，语气真诚不机械。",
            "save_as": "output",
            "next": "end",
        },
        "end": {"type": "end"},
    },
}

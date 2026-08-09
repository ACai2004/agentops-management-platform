# AgentOps — Agent 生命周期管理与持续优化基础设施

> 企业级 Agent Lifecycle Management & Optimization Infrastructure
> 让业务人员（非技术人员）通过「运行 → Trace → 自然语言反馈 → AI 生成修改方案 → 人工确认 → 发布/回滚」的闭环持续优化线上 Agent。

当前状态：**Layer 0 项目脚手架**（后端骨架 + PostgreSQL 本地运行 + Alembic 空迁移）。

- 产品设计文档：[`docs/完全自研AgentOps.md`](docs/完全自研AgentOps.md)
- 技术实现蓝图：[`docs/AgentOps技术实现蓝图.md`](docs/AgentOps技术实现蓝图.md)

## 快速开始（Layer 0）

```bash
# 1. 启动 PostgreSQL
docker compose up -d postgres

# 2. 后端本地运行（conda env: agentops）
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
# GET http://localhost:8000/health  →  {"status": "ok"}
```

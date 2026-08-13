# AgentOps — Agent 生命周期管理与持续优化平台

> Agent Lifecycle Management & Optimization Platform
> 让**不会编程的业务人员**通过可视化工作流，自主搭建 / 测试 / 优化 / 发布 Agent，并用"运行 → Trace → 自然语言反馈 → AI 生成修改方案 → 人工确认 → 发布/回滚"的闭环持续改进线上 Agent。

---

## 核心亮点

- **可视化工作流画布**：拖拽节点、连线搭流程（对话生成 / 判断分支 / 获取数据 / 模板 / 输入 / 结束），成环与悬空实时防呆。
- **反馈驱动优化闭环**：对一条运行记录打一句自然语言反馈 → AI 分析根因、给出结构化修改方案 → 人工确认 → 自动生成新版本 → 发布 / 回滚。**这是平台的核心说服点。**
- **输入随工作流声明**：每个 Agent 在画布上声明自己的输入清单（文本 / 图片 / 数字 / 下拉、必填可选），测试面板按清单动态渲染表单——不同场景输入形式不同，图片优先的流程（如小票识别）无需文本。
- **数据源参数契约**：外部接口（如高德天气）在数据源里声明"参数契约"，工作流节点按契约渲染成中文表单，业务人员只填值、不用懂参数名。
- **版本化发布**：草稿编辑、发布、回滚，每次发布都是完整快照；Agent 支持重命名、软删除（历史数据保留）。

---

## 架构

```
        Frontend 控制台（React + Ant Design + React Flow 画布）
        —— Agent 列表 / 工作流画布 / 测试 / Trace / 优化闭环 / 版本发布 / 资源页
                        ↓  HTTP/JSON
        Backend（Python FastAPI，单进程）
        ┌────────────────────────────────────────────────────┐
        │ api/        路由层                                   │
        │ services/   领域服务（版本 / 发布 / 优化 / 能力 / 知识 / 数据源）│
        ├────────────────────────────────────────────────────┤
        │ runtime/    LangGraph 运行时（读 AgentConfig，产出 Trace）│
        │             llm / decision / http / template / end 节点 │
        ├────────────────────────────────────────────────────┤
        │ llm/        LiteLLM 网关 + 结构化输出通道（重试 / 回喂）    │
        ├────────────────────────────────────────────────────┤
        │ core/       契约（AgentConfig / Trace）+ 四层工作流校验     │
        │ models/     SQLAlchemy 模型（PostgreSQL）             │
        └────────────────────────────────────────────────────┘
        Storage：PostgreSQL（SQLAlchemy + Alembic）
        外部：DeepSeek（文本）+ OpenRouter 视觉模型 + 高德天气等外部 API
```

**设计原则**：管理层自研、运行时用框架（LangGraph 藏在契约后面）；业务代码只依赖 `AgentConfig`（版本快照）与 `Trace`（结构化运行记录）两个契约。

---

## 功能模块

| 模块 | 说明 |
|---|---|
| **可视化工作流** | 节点画布：对话生成（可识别图片）、判断分支、获取数据、模板（纯函数拼接）、输入、结束；拖拽/画线工具连线、选中连线可删除/改分支值、防呆校验、节点"可用输入"预览 |
| **测试面板** | 文本 + 图片（base64 data URL，无需后端存文件）；按输入清单动态渲染表单；运行后展示最终输出 + Trace 步骤时间线 |
| **Trace 运行记录** | 每次运行的完整步骤（节点 / 输入 / 输出 / 分支 / 耗时），对齐 OpenInference 语义，为导出可观测系统预留 |
| **优化闭环** | 对 Trace 打自然语言反馈 → AI 生成方案（问题分析 / 根因 / 建议 / 可应用变更列表）→ 人工确认 → 生成新版本 → 发布 / 回滚 |
| **版本发布** | 草稿 / 已发布 / 已回滚状态机；发布前强制校验（含拓扑、语义、资源存在性、必填参数） |
| **知识库** | 业务资料（菜单 / 环境 / 画像）一处维护、跨 Agent 绑定；内容实时引用，改动即生效 |
| **能力库** | 可复用的行为片段：手动创建，或把某节点的提示词"沉淀"成能力复用 |
| **数据源** | 外部 API 连接配置（地址 / 方式 / key / **参数契约**），供"获取数据"节点按名引用；key 集中管理 |
| **Agent 管理** | 新建 / 重命名 / 软删除（历史保留）；输入清单、系统提示词、知识 / 能力绑定均可在界面配置 |

---

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy 2.0 + Alembic · Pydantic v2 |
| 运行时 | LangGraph（StateGraph 编译 WorkflowConfig） |
| LLM 网关 | LiteLLM（DeepSeek 主 + 备用兜底 + OpenRouter 视觉模型） |
| 数据库 | PostgreSQL 16（本地 Docker） |
| 前端 | React + TypeScript · Ant Design · Vite · @xyflow/react（React Flow） |

---

## 快速开始

> 需要：Docker（跑 PostgreSQL）、Python 3.11+、Node 18+。

```bash
# 1. 启动 PostgreSQL
docker compose up -d postgres

# 2. 后端
cd backend
pip install -e ".[dev]"
cp ../.env.example ../.env    # 填入 DEEPSEEK_API_KEY、OPENROUTER_KEY（视觉）
alembic upgrade head
uvicorn app.main:app --port 8000

# 3. 种子数据（创建「餐后漫谈助手（演示）」Agent + 知识 + 高德天气数据源）
python scripts/seed_demo.py

# 4. 前端（另开一个终端）
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

---

## 5 分钟演示：餐后漫谈助手

1. 打开「餐后漫谈助手（演示）」→ **工作流**页签，看到画布流程：
   `开始(输入) → 订单理解(视觉+菜品匹配) → 获取数据(高德天气) → 体验理解 → 对话规划 → 模板(Prompt Assembly) → 结束`
2. **测试**页：上传一张小票照片（可选填补充文本）→ 运行 → 查看 Trace：
   - 订单理解：识别小票、**匹配到菜单里的菜品标准名**（菜品检索在视觉识别这一步完成）；
   - 获取数据：调用高德返回实时天气；
   - 体验理解 / 对话规划：两层推测（只输出可能性、不假设）。
3. 最终输出 = 组装好的 **Runtime Prompt**：静态 System Prompt + 分隔符 + 三层动态上下文（模板节点纯函数拼接，不经 LLM）。
4. 对这条运行打反馈 →「优化」→ AI 给出方案 →「应用生成新版本」→ 发布 / 回滚，体验完整闭环。

---

## 目录结构

```
├── docker-compose.yml          # postgres（本地）
├── .env.example
├── backend/
│   ├── app/
│   │   ├── core/               # 契约 / 四层校验 / 模型能力登记
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── runtime/            # LangGraph 运行时（compiler / nodes / runner）
│   │   ├── llm/                # LiteLLM 网关 + 结构化输出
│   │   ├── services/           # 领域服务
│   │   └── api/                # REST 路由
│   ├── alembic/                # 数据库迁移
│   ├── scripts/seed_demo.py    # 种子数据
│   └── tests/                  # pytest（70+）
└── frontend/
    └── src/
        ├── editor/             # 工作流画布（React Flow / 序列化 / 配置面板 / 变量插入 / 连线组件）
        ├── pages/              # 控制台页面
        └── api/                # API client
```

---

## 测试

```bash
cd backend
pytest            # 70+ 用例（契约 / 校验 / 运行时 / 发布 / 闭环 / 输入 / 模板 / 数据源）
```

---

## 边界与演进（未实现 / 规划）

- **认证与权限**：当前无登录，发布 / 回滚的 `approved_by` 字段已预留审批语义。
- **中途"向用户提问"节点**（Human-in-the-loop）：当前测试是单次运行，输入在开头收集；流程中途"意图识别后再索要输入"为后续演进。
- **知识检索（RAG）**：当前知识整份注入上下文；知识量变大后演进 pgvector 向量检索。
- **真实语音通话**：当前产出"对话脚本 / Runtime Prompt"，真实语音链路（ASR / TTS / 电话）为后续。
- **灰度发布**：`release_ratio` 字段已预留，本地恒 100%。
- **多实例部署**：当前单进程，会话级并发后续用消息队列。

---

## 已知技术取舍

- **DeepSeek 偶发空返回**：LLM 节点对空输出自动重试（最多 5 次、回退递增并提示模型），降低整条流断掉概率。
- **结构输出健壮性**：`call_structured` 剥离 markdown 代码围栏、校验失败回喂重试、`max_tokens` 防截断；JSON 模式下自动补 "json" 引导，满足 DeepSeek `response_format` 的硬性要求。
- **保存不拦逻辑问题**：工作流搭到一半（缺分支、必填参数没填等）随时可保存；拓扑 / 语义 / 必填问题在**测试运行**与**发布**时统一校验提醒，业务人员不会被编辑过程卡住。
- **http 节点失败不中止**：外部 API 异常时存 `{"error": ...}` 并继续，由下游 LLM 优雅处理。
- **数据源 key**：存放在数据源表 / `.env`，绝不写入版本库。

# ServiceFlow

## Project identity and runnable delivery

ServiceFlow is an **enterprise Agent + backend integration** project for
synthetic campus IT and teaching-support tickets. A bounded LangGraph
Coordinator routes only to fixed Specialists: ticket lookup against the Java
authority, evidence-grounded support knowledge, notification summary, or a
high-risk human handoff. It is deliberately not presented as an autonomous
multi-worker or free-negotiation Agent platform.

The Java service owns authentication, RBAC, ticket state changes, PostgreSQL
persistence, Outbox/Inbox idempotency, RabbitMQ publishing and notification
read models. The Python service owns bounded orchestration, risk policy,
specialist isolation, safe memory/checkpoint boundaries, request Harness and
safe Trace. This keeps authorization and writes in Java rather than allowing
the Agent to bypass business ownership.

GitHub Actions now build/test all three deliverables: Java, Python Agent and
Vue. A no-secret local Compose demonstration is included:

```powershell
docker compose up --build
```

It starts PostgreSQL, RabbitMQ, the Java business service, Python Agent and
Vue at `http://localhost:8081` (RabbitMQ management at `http://localhost:15672`).
The Compose profile uses synthetic/local credentials, turns model calls off,
and keeps the Outbox scheduler off to avoid unexpected delivery side effects.
It proves a reproducible local topology only; it does not prove production
throughput, multi-instance recovery or all optional model integrations.

## Security and observability boundary

Tool contracts now follow the same pattern as JobScope: tool-owned names,
descriptions and Pydantic argument schemas are registered into the Planner
prompt, then validated locally before bounded Graph execution. Trusted identity
and credentials remain runtime-only. This is schema-guided JSON planning, not
native API function calling. See [the unified tool contract](docs/agent-tool-definitions.md).

The Agent exposes request-scoped Harness counts/limits and a redacted
Coordinator Trace; retrieval traces identify strategy stages without exposing
credentials or raw protected ticket content. They are complementary to, not a
replacement for, production OpenTelemetry/Langfuse backends. Existing security
tests cover JWT/RBAC ownership, Risk Guard to human handoff and tool boundary
failures. Document-layout RAG robustness is intentionally concentrated in
JobScope so the two repositories retain distinct interview value.

See [`docs/final-delivery.md`](docs/final-delivery.md) for the current
architecture, demo sequence, verification commands, and explicit capability
boundaries.

面向公开演示与合成校园 IT、教学服务场景的双服务 Agent 系统。它不连接学校真实账号、课程、校园卡或设备，也不会自动执行高风险外部操作。

## 当前实现

- `business-service/`：Java Spring Boot 权威业务服务。包含工单创建、查询、状态机、JWT 与角色授权、Outbox、RabbitMQ 投递、Inbox 幂等、通知读模型。
- `agent-service/`：Python FastAPI 编排服务。包含 LangGraph Coordinator、Ticket / Knowledge / Notification 三个 Specialist、风险拦截、工单查询后的知识跟进、知识导入、BM25 与 OCR fallback。
- OCR：扫描 PDF 会先经过像素上限保护，再渲染页面并调用视觉 OCR；真实 Smoke、黄金文本、CER/WER 与关键字段 Exact Match 报告均可独立运行。
- RAG：知识材料经过 Artifact、Parser、ParsedDocument、Article、Fragment-aware Chunk 后进入 Current Corpus，并提供带来源位置的 Citation。

## 当前多 Specialist 协作边界

```text
用户问题
  ↓
Coordinator / Triage
  ├─ Ticket Specialist → Java 工单读取
  │                        ↓（可选）
  │                  Knowledge Specialist 补充处理指引
  ├─ Knowledge Specialist → 基于 Citation 的知识问答
  ├─ Notification Specialist → Java 通知摘要
  ├─ Risk Handoff Guard → 结构化人工处理指引
  └─ Refuse → 明确拒答
```

已实现的是一个有界、可测试的多 Specialist 工作流；它并不是已经具备持久化恢复能力的自主 Multi-Agent 平台。

## 能力边界

- 持久化 Checkpoint 与跨进程恢复；
- 自主创建任务、开放式多 Agent 协商或分布式 Agent Worker 协调；
- 生产级多 Worker 吞吐、故障恢复与压力测试；
- 真实校园敏感数据上的质量验证。

持久化人工交接任务、运行 Trace 和 Vue 前端工作台已实现；它们不等于生产级运营平台或完整自主 Multi-Agent 能力。

## 目录与端口

```text
business-service/  Java Spring Boot 业务服务，默认 8120
agent-service/     Python FastAPI / LangGraph 服务，默认 8121
frontend/          Vue 3 工作台
docs/              计划、复习与交付文档
```

## 前端覆盖的业务路径

Vue 工作台目前覆盖学生创建、查看和关闭自己的工单，支持人员查看队列、领取并推进状态；也提供 Agent 协同、知识问答与带来源展示、知识导入、通知、持久化人工交接任务和验证边界页面。前端的工单权限只是交互层提示，最终授权仍由 Java 服务执行。

## 本地启动

需要 JDK 17、Maven、Python 3.12、Node.js，以及可访问的 PostgreSQL 和 RabbitMQ。数据库和 Broker 可运行在单独虚拟机中；本仓库不安装或启动它们。

1. 在 `business-service/src/main/resources/` 将 `application-local.yml.example` 复制为 `application-local.yml`，填写你自己的数据库与 RabbitMQ 地址、用户名和密码。这个本地文件已被 Git 忽略。
2. 在 `business-service/` 执行 `mvn spring-boot:run`。
3. 在 `agent-service/` 将 `.env.example` 复制为 `.env`，按需配置模型，然后安装项目依赖并运行 `uvicorn app.main:app --host 127.0.0.1 --port 8001`。
4. 在 `frontend/` 将 `.env.example` 复制为 `.env.local`，执行 `npm install` 和 `npm run dev`。

所有模型开关默认关闭。`.env`、真实密钥、个人本地配置和运行日志不应提交到 GitHub。项目只使用合成校园支持场景演示，不要导入真实学生隐私或生产凭据。

## 验证与限制

新增公开校园 FAQ 离线检索对照：从26个高校官网页面整理51个答案证据单元，冻结153题（直接、口语、约束三种问法），调用真实 Embedding 与 Reranker。

| 策略 | Recall@5 | MRR@5 | nDCG@5 |
| --- | ---: | ---: | ---: |
| BM25 | 0.9085 | 0.7795 | 0.8122 |
| Dense | 0.9739 | 0.8749 | 0.9004 |
| Hybrid/RRF | 0.9739 | 0.8419 | 0.8756 |
| Hybrid+Rerank | 1.0000 | 0.9223 | 0.9421 |

Hybrid+Rerank 相对 BM25 的 MRR@5 提升18.3%。这是由Agent依据公开原文编写并核验来源的自建评测集，尚未经过独立人工标注审核；其结果描述该固定集的检索表现。数据、配置、配对置信区间和完整退化记录见 [评测说明](docs/public-campus-retrieval-benchmark-v1.md)及 [逐题报告](agent-service/reports/public-campus-retrieval-v1-real-20261012.json)。原始HTML和模型缓存不入库，也不改变在线知识库。

- Agent 单测：`python -m unittest discover -s tests -v`（如本地 `.env` 已启用模型，先设置 `PYTHON_DOTENV_DISABLED=true`，避免测试误连真实模型）。
- JobScope 单测与两个 Vue 前端的构建命令见各自 README。
- Java `mvn test` 默认运行单元/进程内测试；显式启用的 PostgreSQL/RabbitMQ 集成 Smoke 需要独立环境，不能把跳过的 Smoke 计作通过。

项目使用的是有边界的 Coordinator + Specialist 工作流，支持 PostgreSQL Checkpoint 与按主体隔离的长期偏好；不提供开放式 Agent 协商、自主任意创建任务或生产级多 Worker 协调。验证环境不是生产环境。

## pgvector 与证据文档工作台

新增可选 pgvector 后端：离线向量快照原子保存，在线余弦排序由 PostgreSQL 执行；模型身份、维度与 Corpus 不匹配时拒绝旧索引，不静默回退。原 JSON 后端保留。

公共知识报告支持生成、结构化章节编辑/批注、修改预览、明确确认、版本历史、删除及 Word 导出。报告 owner 来自 Java 验证的主体；JWT 不传入公共知识生成器，工单正文不进入报告。当前在线演示 Corpus 为演示资料，报告会明确标注，不能冒充校园官方指南。

配置见 `agent-service/.env.example`。报告和向量库需要明确配置 PostgreSQL DSN；选择 pgvector 前先启用 `vector` 扩展。在 VM 中从 `agent-service` 目录构建固定导出 worker：

```bash
docker build -f deploy/report-export/Dockerfile -t agent-report-export:local .
bash deploy/report-export/verify-isolation.sh
```

`local` 是开发子进程，不是 OS 沙箱；`docker` 使用本机 daemon，`ssh_docker` 经 SSH 调用 VM 的相同固定隔离 worker。凭据必须放在 Git 外的本地配置，不能提交 SSH 密码、模型 Key 或真实 DSN。worker 不执行模型生成的代码或任意 Shell。

选定真实 Java 登录/JWT、模型、pgvector、报告版本与 SSH-Docker 链路已验证。分项测试、浏览器 Stub 与完整应用验证的边界见[最终验收矩阵](docs/agent-role-enhancement/Agent-岗位补强-最终验收矩阵.md)。同目录归档三天速通计划、教学规则和游标；不宣称生产负载、逃逸安全认证或全部校园问题准确。

# Agent 岗位补强第二阶段

本页保留第二阶段快照。后续 2026-10-13 已完成真实 Java 登录/验签、模型/pgvector/版本事务/SSH Docker 链路，并清理临时账户/报告；当前配置已是 pgvector 与 ssh_docker。当前 Corpus 是有明确标记的演示知识。最新状态以工作区 `docs/Agent-岗位补强-最终验收矩阵.md` 为准，下面旧 local/待验收记录不代表当前状态。

公共校园知识报告已实现生成、结构化修改预览、明确确认、持久化版本、历史查询、删除及 Word 导出。

## 与 JobScope 相同及不同的边界

复用相同的 `ReportContent` 契约、PostgreSQL 事务/版本策略、固定 worker、Docker 约束及 Vue 文档组件；不是建立跨项目共享进程。

入口 `POST /api/v1/knowledge/reports` 经 `CampusSupportTriageRuntime.resolve_owner_id()` 调用 Java 可信主体解析确定 owner。创建文档的 `query` 不包含 owner、原始工具输出或认证字段。

生成阶段只调用**不携带 Authorization 的公共知识 Graph**，只接受带来源的公共知识答复。JWT 用于文档归属验证，不进入文档生成、worker 或正文；工单正文、Trace 不进入文档。危险移交/工单查询结果不能直接导出为公共知识报告。

修改可以调整标题、选取/重排已存在章节、添加明确标注的个人批注，不能替换来源事实/引用。旧提案竞争返回 409；重复确认不重复升版；其他 owner 的报告返回 404。

## 文件与验证

- `agent-service/app/api/public_knowledge_report_api.py`：身份和公共生成边界。
- `agent-service/app/api/report_workspace_api.py`、`app/application/document_workspace.py`：HTTP 生命周期和内容规则。
- `agent-service/app/infrastructure/persistence/postgres_report_store.py`：独立报告表、版本、提案事务。
- `agent-service/app/infrastructure/reports/report_exporter.py`、`report_export_policy.py`、`report_export_worker.py`：受控导出。
- `frontend/src/components/ReportWorkspace.vue`、`views/ReportsView.vue`：报告页面。
- 显式测试库配置下 Agent 非 MCP 全量：**247 passed、2 skipped**。MCP stdio 在获准的非沙箱环境单独重跑：**1 passed**；不把分开测试写成一次全量结果。
- 文档选定测试 **5 passed**：真实 PostgreSQL/HTTP/本地 worker，Java 身份和生成内容有 Stub；新适配器测试验证 JWT 不传给公共生成器、工单 sentinel 不落入报告。
- 两项非文档原外部 Smoke 跳过，不计为通过。
- 前端 build 通过；真实浏览器生成、修改确认、刷新恢复、下载和删除通过，`page_errors=0`。结果 `agent-service/reports/document-browser-20261012/result.json`；身份与生成器使用 Stub，不是生产 JWT/模型链路。

## 未验收项

独立实验 DB 的报告功能已在本地 `.env` 启用。当前 `SERVICEFLOW_DOCUMENT_EXPORT_BACKEND=local` 为开发模式，不称为 OS 沙箱。

2026-10-13 用户在 VM 执行包中的 `verify-isolation.sh`，截图显示 `export=passed`、36843 字节，`isolation=passed`：UID 65534、网络和根目录写入被阻止、禁止新权限、有效 capabilities 为 0。固定 worker 的真实 Docker 分项验证通过；Windows API 到 VM Docker 的自动导出、生产 JWT/模型到隔离 worker 的完整链路尚未验证。详情见工作区 `docs/Agent-岗位补强-Docker隔离实测-2026-10-13.md`。

没有改变原工单 PostgreSQL、RabbitMQ 队列、旧教学游标或用户删除的 `COURSE_CURSOR_DELIVERY_ENGINEERING.md`。没有恢复 Docling/V2。尚未 push 或修改简历。

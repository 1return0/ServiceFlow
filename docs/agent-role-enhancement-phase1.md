# Agent 岗位补强第一阶段

日期：2026-10-12。开发进行中，不宣称本轮全部完成。

## 当前新增

API 与生产 MCP 使用同一个 Dense store 组装函数。可选 `SERVICEFLOW_DENSE_INDEX_BACKEND=pgvector` 与 `SERVICEFLOW_DENSE_POSTGRES_DSN`；默认仍为原 JSON 后端。

离线向量原子写入 PostgreSQL vector 列，在线由 PostgreSQL `<=>` 排序。模型身份、维度、corpus revision/指纹、完整快照身份必须一致；查询失败映射既有知识检索不可用错误，不静默使用 JSON 或旧库。Chunk 和 citation 仍来自已审核 corpus。

目前使用精确余弦检索，不声称 ANN/HNSW、吞吐提升或数据库检索质量提升。向量列与原长期记忆 Store、短期 Checkpoint 表是不同用途。

## 验证

- 除 MCP stdio 测试外 Agent 全量：238 passed、5 skipped。3 项新增 pgvector 真实 Smoke 未配置显式 DSN，跳过不算通过。
- MCP stdio 首次因 Windows 沙箱命名管道权限失败；在获准的非沙箱环境单独重跑：1 passed，使用确定性 Stub，不消耗真实模型额度。
- 原 PostgreSQL 16.14 未改动。用户另行创建独立 `agent-pgvector-lab` 容器，端口 5544，pgvector 0.8.7；已连接该容器完成 `tests/test_pgvector_live_smoke.py` **4 passed**。
- 真实数据库验证覆盖余弦排序/索引隔离、快照事务回滚、旧 reader 拒绝替换后的快照，以及运行时适配器重启复用、corpus 改变拒绝旧索引和显式 refresh。使用固定 Stub 向量，不是模型质量/吞吐评测；测试 schema 已清理。

## 未完成与保护

公共知识文档导出、文档执行隔离及前端联动尚未完成，不将权限/Harness 描述为 OS 沙箱。

既有用户删除 `docs/COURSE_CURSOR_DELIVERY_ENGINEERING.md` 保持原样。不改变业务 PostgreSQL/工单、RabbitMQ 队列、默认运行配置。不恢复 Docling/V2。尚未 push。

独立三天补充教学计划位于工作区 `docs/Agent-岗位补强-三天学习计划.md`，不覆盖旧游标。

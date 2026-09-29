# Agentic RAG 范围冻结（2026-09-27）

## 已实现

- Current Corpus 上的 BM25 检索、真实 OpenAI 兼容 Embedding、离线 Dense 索引和 BM25 + Dense RRF。
- Hybrid 候选 Rerank；线上 Reranker 不可用时保留 Hybrid 顺序，并返回 `hybrid_rerank_degraded` Trace。
- Corpus 指纹、Embedding 身份、索引持久化与陈旧索引拒绝语义。
- 受控二次检索：只有初检证据数低于门槛时才至多再检索一次；可选 Query Rewrite 不改变来源或权限范围。
- 基于最终检索命中的程序化 citation；无命中时在调用回答模型前返回 `insufficient_evidence`。
- 检索阶段 Trace：Hybrid、初检证据门槛、改写、二检、Rerank、回答或拒答。

## 已有证据

- 自动化测试覆盖检索、索引身份失效、RRF、Rerank 降级、受控二检、引用边界和稳定失败码。
- 真实模型检索对比报告：[retrieval-comparison-real-20260927.json](../agent-service/reports/retrieval-comparison-real-20260927.json)。
  - 真实 Embedding 与真实 Rerank 均请求成功。
  - 对同一评测集分别运行 BM25、Dense、Hybrid、Hybrid + Rerank。
  - 评测集 SHA-256、Corpus fingerprint 和模型身份由报告/配置共同固定。

## 不能夸大的结论

- 当前检索黄金集只有 3 个简单案例，四种策略均为 1.0；它只证明链路连通和指标计算，不足以比较策略优劣或证明 Reranker 收益。
- 当前真实报告是检索评测，不等价于真实在线回答模型、完整 FastAPI 请求、浏览器或并发压测通过。
- 引用 ID 来自最终检索结果，能够阻止模型编造未检索到的 ID；不能单独证明回答的语义蕴含、来源时效性或多个来源冲突处理正确。
- JSON Current Corpus 和本地 JSON Dense 索引适合单机演示；未实现多 Worker 共享索引、分布式协调或生产级向量数据库运维。
- Query Rewrite、Reranker 降级与索引陈旧边界已有代码/自动化测试；尚未把每一种故障都在真实外部服务上重复压测。

## 允许的 P0 修复

仅允许修复会导致以下契约失真的缺陷：

1. 陈旧或身份不匹配的 Dense 索引被静默使用；
2. Reranker 失败被记为正常 Rerank 成绩；
3. 无证据时仍调用回答模型；
4. citation 指向最终检索范围之外的 Chunk；
5. 外部模型/索引失败泄露敏感响应或没有稳定错误码。

除上述 P0 外，不再在第 9 周新增检索功能；后续进入第 10 周校园支持业务闭环。

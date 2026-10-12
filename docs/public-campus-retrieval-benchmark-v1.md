# ServiceFlow 公开校园 FAQ 检索评测 v1

## 冻结方法（结果产生前确定）

从北京师范大学信息网络中心官网的 26 个公开页面整理 51 个答案证据单元。每单元有直接问法、口语描述、约束区分三种问法，共 153 题。它覆盖 VPN、无线网络、门户账号、邮箱、人脸门禁、校园卡和访客服务；不覆盖全部校园业务。

材料为依据原文整理的答案摘要，问题与相关性标注由 Agent 编写，`annotation_status=source_grounded_agent_authored`、`human_reviewed=false`。原文支持词已逐条与下载页面核验；核验来源词不能代替独立人工对全部语义与相关性判断的审核。它是**自建公开资料评测集**，不是官方发布的 IR benchmark，也不是用户真实问题集。多个答案均能完整回答时保留多个相关标签。未标注的结果不能被证明全部不相关。

主评测在固定 Top-5 下比较项目原有 BM25、Dense、Hybrid/RRF、Hybrid+Rerank 四种实现。四者使用完全相同的 51 个证据单元和 153 条查询；原问题、改写问题和标注均不进入索引正文。RRF 各分支候选数20，rank constant60，精排候选数10；保留当前配置，不按本集得分调参。

数据在模型调用前冻结，报告记录 dataset hash、corpus fingerprint、来源快照 hash、模型配置及检索代码 hash。模型调用成功结果在单独的忽略入库缓存中存储，配置或语料变化不会沿用旧缓存。Embedding 和 Reranker 均调用项目实际配置的远程模型；Reranker 不允许静默降级。云服务模型 revision 是配置标签，不能当作已经锁定供应商模型权重的证明。

报告计算 Recall@5、MRR@5、nDCG@5，以及三种问法的分层结果。置信区间采用逐来源网页的配对 cluster bootstrap（26组、10,000次、固定种子20261012）；同一原文的多条问题一起重采样，避免将153条改写问题视为完全独立的样本。预先报告 Hybrid/BM25、Hybrid+Rerank/BM25、Hybrid+Rerank/Hybrid、Hybrid+Rerank/Dense 四组差值。

## 运行方式

在 `agent-service/` 下运行：

```powershell
# 第一次下载源页面，核验支持词并生成来源清单；原始HTML只保存在本地缓存。
py -3.12 -m scripts.run_public_campus_retrieval_benchmark --collect-sources

# 使用 .env 中已经配置好的真实 Embedding / Reranker；已有完整报告禁止覆盖。
py -3.12 -m scripts.run_public_campus_retrieval_benchmark
```

来源清单已经入库，复现检索评测无需重新下载页面；数据摘要、问法、标签、来源链接均在 [benchmark.json](../agent-service/data/retrieval-evaluation/public-campus-v1/benchmark.json) 中。原始页面位于 `data/retrieval-evaluation/.cache/public-campus-sources/`，不会上传到 GitHub。模型向量和请求结果同样只缓存于 `.cache/`。生产知识库和在线索引不参与这次数据导入，不会因本实验改变。

来源页面包含不同年份的历史软件说明和政策，某些内容已过时。这些固定快照用于检索实验，不能直接当作今天的校园服务指南。Source URL 和 section 只证明检索证据有可定位出处；本轮不测 OCR、解析、模型最终回答准确率或生成答案的引用正确率。

简历可以选取该固定集上有证据支持的提升，注明自建公开校园 FAQ 集和比较基线。完整实验报告保留所有策略、分层结果和退化案例；不将单个 Smoke、小样本满分或自建集结果包装成生产效果。

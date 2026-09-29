<template>
  <section>
    <p class="eyebrow">Evidence Boundary</p>
    <h1>验证边界</h1>
    <p>这个页面用于区分“已验证的最小链路”和“尚不能宣传为生产能力”的部分，不展示未经后端评测接口提供的虚构指标。</p>
    <div class="two-column">
      <article class="result-card">
        <h2>已有选定 Smoke</h2>
        <ul>
          <li>PostgreSQL：Human Handoff 的创建、领取与解决。</li>
          <li>RabbitMQ：选定 Outbox/Inbox 消费与去重场景。</li>
          <li>OCR：扫描 PDF 到 Current Corpus 的最小导入链路。</li>
          <li>Multi-Agent：Coordinator Trace、风险交接与黄金案例框架。</li>
        </ul>
      </article>
      <article class="result-card">
        <h2>仍需明确的边界</h2>
        <ul>
          <li>运行中 Java HTTP 登录 401 的根因尚未闭环。</li>
          <li>当前没有后端评测报告 API，因此不在浏览器伪造 Recall、CER 或 Agent 准确率。</li>
          <li>没有生产并发压测、分布式 Checkpoint 或真实校园敏感数据验证。</li>
          <li>Outbox + Inbox 是至少一次投递下的去重设计，不是 Exactly-once。</li>
        </ul>
      </article>
    </div>
  </section>
</template>

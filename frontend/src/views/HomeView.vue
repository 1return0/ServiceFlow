<template>
  <section>
    <p class="eyebrow">Campus Service Operations</p>
    <h1>校园服务协同工作台</h1>
    <p>
      以一个统一会话调用 Java 业务服务与 Python Agent 服务。页面只展示它们返回的真实结果，不在浏览器保存服务端密钥。
    </p>
    <div class="card-grid">
      <RouterLink class="card" to="/tickets"><strong>工单闭环</strong><span>提交、跟踪、领取和推进工单状态</span></RouterLink>
      <RouterLink class="card" to="/assistant"><strong>协同助手</strong><span>工单、知识、通知与人工交接路由</span></RouterLink>
      <RouterLink class="card" to="/notifications"><strong>通知</strong><span>查看未读状态并标记已读</span></RouterLink>
      <RouterLink class="card" to="/evidence"><strong>验证边界</strong><span>区分真实 Smoke 与尚未验证的生产能力</span></RouterLink>
    </div>
  </section>
</template>

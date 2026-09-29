# ServiceFlow Frontend

Vue 3 + TypeScript + Vite 前端。浏览器只读取服务地址，不保存任何模型 API Key、数据库密码或 JWT 签名密钥。

## 本地启动

1. `Copy-Item .env.example .env.local`
2. `npm install`
3. `npm run dev`

服务地址放在 `.env.local`：

- `VITE_AGENT_API_BASE_URL`：Python Agent 服务。
- `VITE_BUSINESS_API_BASE_URL`：Java 业务服务。

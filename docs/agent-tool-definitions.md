# ServiceFlow 与 JobScope 的统一工具契约

两个项目采用相同的工具定义方式：`name`、`description`、Pydantic 参数模型及其 `model_json_schema()`。ServiceFlow 的工具注册表由运行时实际使用的工具实例生成，避免提示词中的工具清单与执行器各自维护。

## 完整链路

```text
bootstrap 创建工具实例
  → AgentToolDefinition.from_tool()
  → AgentToolRegistry.prompt_payload() 输出 available_tools + output_contract
  → ModelTriagePlanner 调用模型
  → Registry.decode() 校验选择、注册名称、参数模型
  → TriagePlan
  → LangGraph 条件路由 / Specialist
  → Tool.invoke() 再次校验参数
  → Tool.execute() 调用业务服务或知识问答
```

| 工具名 | 模型可提供的参数 | 运行时路由 |
| --- | --- | --- |
| `lookup_ticket` | `ticket_id`：UUID | `lookup_ticket` |
| `answer_support_knowledge` | `question`：非空，最多 2000 字符 | `answer_support_knowledge` |
| `get_notification_summary` | 空对象 `{}` | `get_notification_summary` |
| `create_human_handoff_task` | `handoff_reason`：限定风险枚举 | `handoff_to_human` |

模型不能提供 `authorization`、`owner_id`、`roles`、`request_id` 或检索深度。需要身份的工具从可信调用上下文取得 Authorization；人工任务的 request_id 由运行时注入。匿名高风险请求仍只返回交接指引，不创建 Java 人工任务。风险 Guard 仍在 Planner 前执行；Java 仍负责最终授权。

## 模型输出示例

```json
{
  "decision": "call_tool",
  "reason": "用户询问公开校园网络使用方法",
  "tool_name": "answer_support_knowledge",
  "arguments": {"question": "如何重置校园网络访问？"},
  "follow_up_knowledge": false
}
```

未知工具、额外参数、非法 UUID、不支持的风险原因、非法知识跟进会被拒绝，并转换为原有 Planner 输出契约异常，由现有降级策略处理。规则 Planner 不需要调用模型，继续生成原有 TriagePlan。已有 Checkpoint 中没有 knowledge_question 的计划继续使用当前用户问题。

这属于 **Prompt 中的工具 Schema + 结构化 JSON 规划 + 本地校验执行**，不是模型 API 原生 `tools/tool_calls` Function Calling，也不是通过 MCP Client 调用这些内部工具。公开知识 MCP Server 保持独立协议入口，未更改协议工具名。

## 核心文件

- `agent-service/app/application/agent_tool_planning.py`：注册、Schema、提示载荷及模型选择校验。
- `agent-service/app/application/model_triage_planner.py`：主 Planner，提示版本 `campus-support-triage-prompt-v6`。
- `agent-service/app/application/model_ticket_lookup_planner.py`：单工单 Planner 复用同一注册逻辑，版本 `ticket-lookup-planner-prompt-v2`。
- `agent-service/app/application/*_tool.py`：各工具的参数模型、元信息与 invoke/execute。
- `agent-service/app/bootstrap.py`：同一组工具实例用于生成契约并注入执行节点。
- `agent-service/app/application/workflows/campus_support_triage_graph.py`：保留受控 Graph 路由。
- `agent-service/tests/test_agent_tool_planning.py`：契约、越界参数及 Planner 到执行的回归测试。

## 本次验证边界

关闭本机 .env 加载及外部模型/数据库功能后，Agent 测试（不含 MCP 子进程测试）为 257 passed、10 skipped；MCP stdio Stub 子进程测试单独为 1 passed。未运行真实模型质量评测或真实 Java/PostgreSQL 全链路验证，历史检索指标不因这次契约调整而更新。

面试表述：两个项目都将工具名、描述和参数 Schema 统一注册到 Planner；模型只提出调用意图，运行时校验白名单和参数，再通过受控工作流调用工具，身份与权限不由模型生成。

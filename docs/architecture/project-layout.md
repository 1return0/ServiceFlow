# ServiceFlow 目录导航

## 分类原则

没有唯一的“GitHub 标准目录”。本项目保留三个可运行组件：Java 权威业务、Python Agent、Vue 前端；Java 采用“业务模块内分层”，Python 保留 API / Application / Domain / Infrastructure 边界，在较大的层内按职责分类。

参考的是这些项目的组织规律，不照搬其数据库、框架或业务实现：

- [Spring Boot 代码组织建议](https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html)：启动类放根包，按业务能力组织子包。
- [Spring Petclinic](https://github.com/spring-projects/spring-petclinic/tree/main/src/main/java/org/springframework/samples/petclinic)：保留业务模块边界，不把所有功能强行堆入同一层目录。
- [FastAPI 官方全栈模板](https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend/app)：API、配置/核心、模型等职责分开。本项目已有领域和基础设施边界，不为模仿模板重新改写架构。

## Java：先找业务模块，再找层

根包：`business-service/src/main/java/com/serviceflow/business/`。

```text
business/
├── ServiceFlowBusinessApplication.java
├── api/                    系统接口
├── config/                 跨模块 Spring 配置
├── common/                 统一响应、异常处理、MyBatis 类型处理
├── auth/                   认证业务
│   ├── config/
│   ├── controller/
│   ├── dto/req/            登录请求
│   ├── dto/resp/           登录及可信主体响应
│   ├── dao/entity/         用户表实体
│   ├── dao/mapper/         用户数据库访问
│   ├── exception/
│   ├── security/           JWT Filter
│   └── service/impl/       认证应用服务及实现
└── ticket/                 工单业务
    ├── config/
    ├── controller/         工单、通知、人工交接 HTTP 入口
    ├── dto/req/            创建工单、状态更新等请求
    ├── dto/resp/           工单、通知、人工交接响应
    ├── dao/entity/         工单、Outbox、Inbox、通知等表实体
    ├── dao/mapper/         对应 Mapper
    ├── domain/             状态与角色等业务枚举
    ├── exception/
    ├── service/
    │   ├── impl/           工单业务实现
    │   ├── handoff/        人工交接服务
    │   └── notification/   通知查询服务
    └── manager/mq/
        ├── event/          消息载荷契约
        ├── outbox/         租约、发布、投递调度及摘要
        └── inbox/          消费入口、去重及通知处理链
```

`service` 负责业务能力，`dao` 负责数据库，`manager/mq` 封装消息协作细节；不能因为类名包含 Service 就把所有投递协调代码视为工单业务规则。本次没有新增空接口、改变事务或修改授权逻辑。

Mapper XML 仍在 `business-service/src/main/resources/mapper/`，数据库迁移仍在原位置。已同步更新 Java package/import、MapperScan、XML namespace/resultType/type 及对应测试包；启动类仍在根包。

## Python：先找层，再找职责

根包：`agent-service/app/`。

```text
app/
├── main.py                 FastAPI 启动入口
├── bootstrap.py            服务组装、Graph 和依赖构造
├── config.py               配置读取
├── api/                    HTTP 路由
├── mcp/                    MCP 服务及 stdio 入口
├── domain/                 领域数据、协议与值对象
├── application/
│   ├── agent/              Planner、Specialist、Harness、Trace、风险策略
│   ├── workflows/          LangGraph State、节点、边及编译
│   ├── tools/              工具定义与有界执行
│   ├── memory/             长期偏好、安全对话轮次
│   ├── knowledge/          导入、解析编排、文章组装和切块
│   ├── retrieval/          BM25、Dense、RRF、精排、二次检索、回答
│   ├── reports/            版本化报告工作区业务
│   └── evaluation/         Planner、多 Agent、OCR 和检索评测
└── infrastructure/
    ├── clients/            Java 业务服务 HTTP 适配器
    ├── parsers/            PDF/HTML/Office/OCR fallback 及页面渲染
    ├── models/             Qwen/兼容模型适配器、重试策略
    ├── persistence/        JSON、文件、PostgreSQL、pgvector 存储适配器
    └── reports/            本地/SSH 导出、隔离策略、固定 worker
```

`domain` 是业务数据含义；`infrastructure/models` 是外部模型 API 的调用实现，二者不是同一类“模型”。原 `app/planning`、`app/tools`、`app/workflows` 只有占位说明，实际工作流一直在 `application/workflows`；已删除这三个未使用的占位包。

## 经常要找的代码

| 想找什么 | 当前入口 |
| --- | --- |
| 工单 HTTP 接口 | [TicketController](../../business-service/src/main/java/com/serviceflow/business/ticket/controller/TicketController.java) |
| 创建、认领、修改工单 | [TicketServiceImpl](../../business-service/src/main/java/com/serviceflow/business/ticket/service/impl/TicketServiceImpl.java) |
| 工单表及 Mapper | [TicketEntity](../../business-service/src/main/java/com/serviceflow/business/ticket/dao/entity/TicketEntity.java)、[TicketMapper](../../business-service/src/main/java/com/serviceflow/business/ticket/dao/mapper/TicketMapper.java) |
| 工单状态 | [TicketStatus](../../business-service/src/main/java/com/serviceflow/business/ticket/domain/TicketStatus.java) |
| Outbox 投递 | [TicketOutboxDeliveryService](../../business-service/src/main/java/com/serviceflow/business/ticket/manager/mq/outbox/TicketOutboxDeliveryService.java) |
| MQ 消费入口 | [TicketStatusChangedInboxConsumer](../../business-service/src/main/java/com/serviceflow/business/ticket/manager/mq/inbox/TicketStatusChangedInboxConsumer.java) |
| Agent Graph | [campus_support_triage_graph.py](../../agent-service/app/application/workflows/campus_support_triage_graph.py) |
| 模型 Planner | [model_triage_planner.py](../../agent-service/app/application/agent/model_triage_planner.py) |
| 工具名、描述、参数契约 | [agent_tool_planning.py](../../agent-service/app/application/agent/agent_tool_planning.py)、[ticket_lookup_tool.py](../../agent-service/app/application/tools/ticket_lookup_tool.py) |
| 请求级 Harness | [agent_harness.py](../../agent-service/app/application/agent/agent_harness.py) |
| Checkpoint、长期记忆存储 | [postgres_checkpointer.py](../../agent-service/app/infrastructure/persistence/postgres_checkpointer.py)、[postgres_long_term_memory_store.py](../../agent-service/app/infrastructure/persistence/postgres_long_term_memory_store.py) |

逐文件迁移关系见 [package-moves.json](package-moves.json)。本地额外脚本若仍导入旧模块，请按此表更新；不保留旧路径兼容壳，避免再次出现两套目录。

## 其他目录与清理边界

- `frontend/src` 原有 api/components/views/router/config/session 已按职责分层，本次不为统一名字搬动它们。
- `tests`、`scripts`、`data`、`reports` 保留各自职责；冻结的评测数据和历史报告内容不随模块名迁移而改写。
- 空目录清理列表见 [removed-empty-directories.json](removed-empty-directories.json)：31 项，包含搬空的 Java 包、原有空占位/渲染目录、废弃占位包的字节码缓存及包目录。
- 仅清除了三个废弃占位包残留的可再生 `.pyc`；没有清理用户文件、`.env`、依赖、数据库或其他缓存。迁移源码可从原 Git 版本恢复，缓存可由 Python 再生成。
- 本次开始前已有的 `docs/COURSE_CURSOR_DELIVERY_ENGINEERING.md` 删除保持不变。

## 验证

本次实跑结果：Python 261 passed / 10 skipped（另有 150 个 subtest 通过）；Java clean test 67 项中 55 通过 / 12 跳过、0 failure/error；前端构建通过；Python wheel 构建通过。跳过的外部依赖验证不计为通过。新增目录测试校验全部迁移目标存在、旧源路径消失、占位包已移除及 Docker worker COPY 路径有效。

- Python 按既有 CI 开关 `PYTHON_DOTENV_DISABLED=true` 运行，避免读取开发机真实模型/数据库配置；外部依赖 live 用例未启用，不冒充通过。
- Java 使用 clean test，避免旧包的 target 字节码掩盖迁移错误。
- 前端执行 npm run build；未声称做了数据库/MQ/模型的真实端到端运行验收。

仅整理文件位置和引用，未改变 HTTP 路径、数据库表、权限、Graph 边、事务与模型调用策略。未提交或推送 GitHub。

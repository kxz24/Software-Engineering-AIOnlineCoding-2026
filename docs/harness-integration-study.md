# 工程题 AI harness 集成实验

本分支是本地实验，基于 `ljy_feat/agent-learning-experiment` 并纳入多文件工程题支持。目标是让助教在考生明确授权后，能在公开工程工作区里运行命令或修改文件，同时留下可核查的操作记录。

## 选型与边界

实验采用 [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) 2.4.6 的 `DefaultAgent`、`LitellmModel` 和 `DockerEnvironment`。它提供现成的模型、命令执行和循环控制；项目只实现考试权限、文件同步、持久化和 UI。没有将其整套部署到 Django Web 进程，而是交给专用 Celery worker。原有问答与审查流程继续处理“只回答”请求。

每轮考生显式选择“只回答 / 运行 / 修改”。`closed` 禁止 AI；`limited` 只能回答，服务器拒绝运行与修改；`open` 中的工程题才可将运行或修改送入 harness。文件级修改还要求指定当前文件。工程运行结束后不写回任何文件；工程修改仅在 agent 正常提交结果、文件仍是原版本、且改动没有越过授权范围时写回 `WorkspaceFile`，并生成 `CodeChange`。工作区只装载题目公开文件，不装载隐藏测试和评分材料。

执行容器使用无网络、只读根文件系统、非 root 用户、去除 Linux capabilities、进程/CPU/内存限制以及临时工作区。模型请求在 worker 中发起，API 密钥不进入执行容器。worker 持有 Docker socket，因此它本身必须是受信任的服务；这一点需要在正式部署环境单独审查。

## 请求与记录

1. `POST /api/v1/agent/sessions/{id}/messages` 提交 `content`、`action`，修改时附 `scope` 与 `activeFile`。工程运行/修改返回 HTTP 202 和 `jobId`。
2. 前端轮询 `GET /api/v1/agent/sessions/{id}/jobs/{jobId}`，显示状态、步数与最终回复；`POST .../cancel` 可停止任务。已在执行中的模型调用要到下一次命令边界才会响应停止。
3. 服务器保存 `AgentHarnessJob`、各条命令的 `AgentToolCall`、最终 `AgentMessage` 和实际写回的 `CodeChange`。报告把考生请求、AI 实际修改和运行请求分开；构建失败不会被记为成功构建。报告不据此推断学生是否掌握知识。

部署时设置 `AGENT_PROJECT_HARNESS_ENABLED=1`，并配置 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`AGENT_HARNESS_MODEL`。先构建工程题运行镜像，再用 Compose 启动 `agent-worker`。默认最多三条 worker 任务并行，每个执行容器限制 768 MiB、1 CPU；这只约束执行容器，不代表模型 API、MySQL、Redis 与 Web 进程的总资源上限。

## 本地实测

用 Arch Lab 的公开 handout 导入工程题，模拟一名考生通过项目 API 发出两轮请求，模型为网关上的 `DeepSeek-V4.1-Flash-1017`：

| 本轮请求 | agent 自行结束后的可核查结果 |
| --- | --- |
| 仅在 `sim/misc` 运行 `make yas`，不改文件 | 执行 3 步，报告编译到链接阶段时出现 `lineno` 重复定义，`make` 退出码为 2；数据库工作区无改动。 |
| 只将 `PartA/sum.ys` 首行注释改为指定文本，不运行测试 | 执行 3 步，只写回 `PartA/sum.ys`；没有运行测试。 |

两轮报告将调试提问记为 1 次、局部编程请求记为 1 次，并指出“无法判断学生是否独立完成了后续工作”。本地报告生成成功。另一次独立的 Arch Lab 可行性长实验中，mini-SWE-agent 自行结束并经独立自动评分取得 87.67/100；那是完整作业能力测试，不能等同于本平台在每轮授权限制下的成绩。长实验出现过 96 次调用后的网关连接错误，也产生了很大的模型上下文；正式使用需监控费用、延迟和中断恢复。

本分支的回归验证：后端 `agent problem judge` 原有及新增测试共 123 项通过、7 项按既有条件跳过；新增的“构建失败不计成功”针对性测试另行通过。前端生产构建通过；Compose 配置解析通过。上述两轮为真实模型与隔离容器的 API 级实验，尚未代表整套生产 Compose 部署的负载测试。

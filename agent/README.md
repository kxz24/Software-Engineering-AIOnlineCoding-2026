# AI 助教 Agent（`agent/`）

考试平台的 AI 辅助服务：按考试配置的级别提供「无 AI / 给建议 / 直接改代码」三种能力，
并如实记录考生的 token 用量、AI 对代码的修改以及考试期间的对话。

> 当前状态：**后端与前端工作台已接入**（`backend/agent/` + `frontend/src/api/agent.ts`），已通过真实 OpenAI 兼容网关联调。
> 默认 `AGENT_PROVIDER=mock`，未配置 DeepSeek 密钥时也能把对话、工具与用量链路跑通。

## 设计目标

1. **分级**：AI 的权限由考试配置决定，在服务端强制，不依赖前端隐藏按钮。
2. **可审计**：每次模型调用的 token、每次工具调用、每次 AI 改代码、每轮对话都落库。
3. **不泄题**：隐藏用例、判题结果、其他考生数据不进入模型上下文。

非目标：AI 不参与判分；不提供「调用判题接口试跑隐藏用例」的能力；不代替教师做成绩认定。

## 分级设计

现有 `Exam.ai_mode`（`closed / limited / open`）直接映射为三级，语义固定如下：

| `ai_mode` | 级别 | AI 能做什么 | 服务端提供的工具 | 前端表现 |
| --- | --- | --- | --- | --- |
| `closed` | 一级 无 AI | 不能发起模型请求 | 无 | Agent 面板禁用 / 隐藏，接口 403 |
| `limited` | 二级 建议 | 读题面、读当前代码、查提交记录、跑**公开样例**；用自然语言回答当前所问的思路、概念与调试方向，不给可直接照写的实现语句或完整步骤 | `list_files`、`get_problem`、`read_workspace`、`list_submissions`、`run_sample_tests` | 只读对话；回复经审查后展示，没有「应用」按钮 |
| `open` | 三级 协作 | 在二级能力上直接修改工作区代码 | 二级工具 + `write_file`、`apply_patch`、`run_tests` | 展示 diff，「应用 / 撤销」 |

两条硬约束：

- **工具列表由服务端按会话级别生成**：二级请求里根本不存在写文件工具，模型无法绕过。
- **三级写入必须经过服务端**：AI 写的是服务端的 `WorkspaceFile`，同时生成 `CodeChange`
  记录；前端只拉取工作区与修改记录，不直接采用模型输出覆盖编辑器。
- `ai_mode` 在考试发布后冻结；创建会话时把级别快照到 `AgentSession.level`，
  之后修改考试配置不影响进行中的会话。

二级回复先完整生成，再由 `Qwen3.8-Flash` 独立审查。若含可直接照写的语句、
过度完整的解法或超出当前提问，审查意见送回原助教重写一次；再不合格或审查失败，
返回固定的安全提示。未经审查的正文不作为 SSE `delta` 发给考生。
确定性检查额外拦截代码块、行内可执行表达式和超过 450 字的回答。明显要求忽略考试规则的
请求会另记审计日志；普通的代码求助不视为攻击。审查调用的 token 计入用量。
本地可运行 `python scripts/repro_limited_ai.py --fresh-student --problem-index 5
--assert-conservative`，用真实 HTTP/SSE 对双有序数组中位数题做两轮回归。

## 技术选型

| 模块 | 选型 | 说明 |
| --- | --- | --- |
| Agent 服务 | **首版：Django 应用 `backend/agent/`**（SSE 用 `StreamingHttpResponse`） | 先复用主站鉴权、考试状态与 ORM，一个进程即可联调；要独立部署时再拆 FastAPI，provider 与工具循环已解耦 |
| 模型调用 | **`httpx` 直连 DeepSeek 的 OpenAI 兼容接口** | 不额外引入 SDK；流式、工具调用与 usage 字段直接解析，mock provider 用于无密钥联调 |
| Agent 编排 | **自写 tool loop** | 工具只有几种，自建循环便于审计、控权限、记 token；不引入 LangChain/LangGraph |
| 鉴权 | 复用主站 JWT | 与 Django 共用 `JWT_SECRET`，请求头沿用「原样放 `Authorization`」的约定 |
| 数据访问 | 直接使用 Django ORM | 与主站同库，避免维护两套 schema |
| 样例执行 | 复用判题沙箱（`judge.sandbox.run_sandbox`） | 只传入 `is_sample=True` 的用例；沙箱不可用时把原因返回给模型 |
| 流式传输 | SSE（`text/event-stream`） | 前端用 `fetch` + `ReadableStream` 解析，`EventSource` 无法携带 Authorization 头 |

> 根目录 README 里写的 LangChain 是最初的占位选型，实际以本文件为准。

## 模型接入（DeepSeek）

- 接口地址：`https://api.deepseek.com`（OpenAI 兼容，`/chat/completions`）。
- 默认模型：`deepseek-chat`（支持 function calling，用于 Agent 循环）；
  `deepseek-reasoner` 仅用于不调工具的代码分析，具体能力以官方文档为准。
- 流式请求：`stream=True` + `stream_options={"include_usage": True}`；
  最后一个 chunk 的 `usage` 包含 `prompt_tokens`、`completion_tokens`、
  `prompt_cache_hit_tokens`、`prompt_cache_miss_tokens`，原样落库。
- 上下文缓存：DeepSeek 自动按前缀缓存；系统提示、题面放在最前面并保持稳定。
- 超时重试：单次 60–120 秒超时，网络错误指数退避最多 2 次；`clientMessageId` 保证幂等。
- 配额：每场考试可为每生设置 `Exam.agent_token_quota`（0 = 不限），超限后拒绝新请求。
- 合规：学生代码属于考试材料。若课程要求数据不出境 / 不用于训练，
  可改用 DeepSeek 开源权重 + vLLM 自部署，接口仍是 OpenAI 兼容，调用层无需改动。

## 架构

```text
浏览器（工作台 Agent 面板 / 提交结果 / 报告）
        │  HTTPS + JWT
        ▼
      Nginx ──/api/v1/──▶ Django（考试、题库、判题、审计）
                                 ├── agent 应用（backend/agent）：会话、SSE、工具
                                 ├──▶ DeepSeek API（流式对话 + 工具调用）
                                 └──▶ 判题沙箱（只跑公开样例）
```

- Django 是权限与数据的唯一权威：考试状态、名单、级别、额度都以主站为准。
- `agent` 应用负责模型编排、工具执行与流式转发；后续若要独立部署，
  可把 provider + 工具循环搬到 FastAPI 服务，接口形状不变。
- 部署时 Nginx 对 SSE 关闭缓冲（`proxy_buffering off; proxy_read_timeout 300s;`），
  gunicorn 的 `--timeout` 同步调到 300s，否则长回复会被 worker 超时杀掉；
  当前每个 SSE 连接会占用一个同步 worker，高并发时再考虑 gevent / 独立 ASGI 服务。

## 数据表

新增在 Django 主站（`judge` / `exam` 应用之外单独建 `agent` 应用更清晰），
迁移文件不入库，与现有约定一致。

| 表 | 关键字段 | 用途 |
| --- | --- | --- |
| `AgentSession` | exam / student / problem、level 快照、provider、model、prompt_version、状态、累计 input/output/cache token、开始与结束时间 | 一场考试中某生某题的一个会话，按 `(exam, student, problem)` 唯一 |
| `AgentMessage` | session、seq、role（user/assistant/tool/system）、content、tool_calls、tool_call_id、usage、token、finish_reason | 完整对话记录，只增不改；`(session, seq)` 唯一 |
| `AgentToolCall` | session、call_id、工具名、参数、结果摘要、是否成功、耗时 | 工具调用明细，便于排查与统计 |
| `WorkspaceFile` | exam / student / problem、path、content、revision | 三级模式的服务端工作区；`revision` 做乐观锁 |
| `CodeChange` | session、文件、revision_before/after、before/after 正文、diff、状态 | 每次 AI 修改的记录，支持撤销，可统计 AI 代码占比 |
| `Exam.agent_token_quota` | 每生本场 token 上限 | 额度控制，0 表示不限 |

Token 一律使用模型返回的 `usage`，不做本地估算；会话表用 `F()` 原子累加，
消息表保留原始 `usage` JSON 便于对账。

## 接口草案

学生端（均需登录，且考试进行中 / 在名单内 / 级别允许）：

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/agent/capabilities?examId=&problemId=` | GET | 当前级别、可用工具、剩余额度、模型 |
| `/api/v1/agent/sessions` | POST | 创建或取回会话 |
| `/api/v1/agent/sessions/{id}/messages` | GET | 对话历史（`afterSeq` 增量拉取） |
| `/api/v1/agent/sessions/{id}/messages` | POST | 发消息，返回 SSE 流 |
| `/api/v1/agent/sessions/{id}/changes` | GET | 本题 AI 修改记录 |
| `/api/v1/agent/changes/{id}/revert` | POST | 撤销一次 AI 修改（三级） |
| `/api/v1/agent/workspace?examId=&problemId=` | GET / PUT | 三级工作区读写（乐观锁） |

教师 / 管理员：

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/exams/{id}/agent/sessions` | GET | 本场考试全部会话（每人 token、消息数、修改次数） |
| `/api/v1/exams/{id}/agent/summary` | GET | 按学生汇总 token、消息数、AI 修改次数与行数 |
| `/api/v1/agent/sessions/{id}/transcript` | GET | 完整对话 + 工具调用 + 修改记录（本人或教师） |
| `/api/v1/exams/{id}/agent/export?format=csv` | GET | 导出统计 / 对话 |

### 发消息的 SSE 事件

```text
event: meta        {"userSeq": 5, "assistantSeq": 6}
event: delta       {"text": "先检查一下输入解析……"}
event: tool_call   {"callId": "call_1", "name": "run_sample_tests", "arguments": {...}}
event: tool_result {"callId": "call_1", "ok": true, "summary": "样例 2：期望 3，实际 -1"}
event: change      {"changeId": 9, "path": "p1_a_plus_b.py", "status": "applied", ...}
event: usage       {"promptTokens": 1800, "completionTokens": 420, "cacheHitTokens": 1200}
event: done        {"assistantSeq": 6, "finishReason": "stop"}
event: error       {"code": "provider_timeout", "message": "..."}
```

约定：

- 同一会话同时只允许一条在途请求，重复发送返回 409；
- 每 15 秒发送 SSE 注释保活，客户端断开即取消上游请求，已产生的 usage 仍要落库；
- 二级永远不会出现 `change` 事件；
- `clientMessageId` 作为幂等键，重试不会产生重复消息。

## 目录

```text
agent/README.md                本设计说明
backend/agent/
├── models.py                  AgentSession / AgentMessage / AgentToolCall /
│                              WorkspaceFile / CodeChange
├── levels.py                  ai_mode → 级别 → 可用工具（权限的强制点）
├── providers.py               MockProvider + DeepSeekProvider（OpenAI 兼容 / SSE）
├── tools.py                   只读工具与 write_file，工具 schema 与执行
├── service.py                 上下文组装、tool loop、用量累计、教师汇总
├── views.py                   学生端 / 教师端接口，SSE 输出
├── urls.py                    路由（/api/v1/agent/...）
└── tests.py                   分级、SSE、工具权限、额度、撤销
```

## 环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AGENT_PROVIDER` | `mock` | `mock` 或 `deepseek`；密钥到位后改成 `deepseek` |
| `DEEPSEEK_API_KEY` | 空 | 模型密钥，只放在服务端 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容接口地址 |
| `AGENT_MODEL` | `deepseek-chat` | 判题循环用支持 function calling 的模型 |
| `AGENT_MAX_OUTPUT_TOKENS` | `4096` | 单次回复输出上限；注意网关把思考 token 也计入，过低会截断正文 |
| `AGENT_MAX_TOOL_ROUNDS` | `6` | 单条消息最多几轮工具调用 |
| `AGENT_HISTORY_MESSAGES` | `40` | 发给模型的历史消息条数上限 |
| `AGENT_REQUEST_TIMEOUT` | `180` | 模型请求超时（秒） |
| `AGENT_PROMPT_VERSION` | `v1` | 提示词版本，写入会话记录 |

`Exam.agent_token_quota` 控制每生每场考试的 token 额度（0 = 不限）。

本地配置：把 `backend/.env.example` 复制为 `backend/.env` 填写即可（`.env` 已被 git 忽略，不会提交）。当前联调使用并行科技提供的 OpenAI 兼容网关
（`https://llmapi.paratera.com`，模型 `DeepSeek-V4-Flash-Vision-Exp`）；换成官方或自建服务只改这三个变量。

## 安全与审计要求

1. 工具集按级别服务端生成；写工具只对三级开放，写入校验 `expectedRevision`。
2. 隐藏用例不进上下文：`get_problem` 只返回公开样例，`run_sample_tests` 只跑公开用例。
   二级回复在服务端经 `agent/policy.py` 过滤：Markdown 代码块、未闭合代码块、
   连续 3 行以上的代码会被替换为提示语；提示词同时要求拒绝「给完整代码」的请求。
3. AI 修改全部经过 `WorkspaceFile` + `CodeChange`，前端不直接采用模型输出。
4. 对话、工具调用、修改记录只增不改；考试结束后冻结，供教师端报告与申诉使用。
5. 额度用尽、模型超时、工具失败都要落状态，不能静默失败。
6. 学生可以通过提示词尝试越权，但越权只能落在文字回复上，改不了工作区。

## 实现进度

- [x] `agent` 应用与五张表 + `Exam.agent_token_quota`
- [x] `capabilities` / `sessions` / 消息历史 / SSE 发送（默认 mock provider）
- [x] 二级只读工具：`get_problem`、`read_workspace`、`list_files`、
      `list_submissions`、`run_sample_tests`
- [x] DeepSeek provider（流式、工具调用、usage 与缓存命中字段）；已通过真实网关联调
- [x] 三级：工作区 API、`write_file`、`CodeChange`、撤销
- [x] 教师端：按考试的用量汇总、会话列表、单会话转录；监考中心「AI 使用」卡片可查看每生
      token、完整对话与 AI 代码修改 diff
- [x] 二级建议模式的完整代码过滤（提示词 + 服务端兜底）
- [ ] `apply_patch`（当前用整文件 `write_file` 代替）
- [ ] `clientMessageId` 幂等与 SSE 保活（当前未使用 / 未发送心跳）
- [ ] 教师端 CSV 导出、考试结束自动冻结会话
- [x] 前端工作台 Agent 面板接入（SSE、工具调用、diff 展示、撤销、token 显示）
- [ ] 节流 / 同会话并发请求保护（当前未限制同会话并发）

## 落地顺序

1. ~~建 `agent` 应用与五张表 + `Exam.agent_token_quota`~~
2. ~~`capabilities` / `sessions` / 消息存储接口，二级只读对话与 token 统计~~
3. 接 DeepSeek：provider 已实现，配置密钥后联调
4. ~~三级：工作区 API、`write_file`、diff 与撤销~~（`apply_patch` 待补）
5. ~~教师端汇总与转录~~；导出与冻结待补

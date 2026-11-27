# 后端（`backend/`）

AICoding 考试平台的后端，提供认证、账号管理与权限分级、题库与测试样例管理、
考试管理与考生作答闭环（创建 / 组卷 / 发布 / 提交收卷）等接口，
容器化判题与 Agent 服务在后续迭代接入。

## 技术栈

- Python 3.11+ / Django 4.2.5 / Django REST Framework 3.15.2
- 认证：PyJWT 签发校验令牌，scrypt 做密码散列（不自建用户表加密体系之外的东西）
- 接口文档：drf-spectacular（Swagger / ReDoc）
- 数据库：开发用 SQLite（`db.sqlite3`），生产用 docker-compose 里的 MySQL 8.1

## 启动

```bash
cd backend
#建议使用conda
pip install -r requirements.txt

python manage.py makemigrations user problem exam agent practice   # 迁移文件被 .gitignore 忽略，需各自本地生成
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

AI 助教需要模型配置：`cp .env.example .env` 后填写 `DEEPSEEK_API_KEY` 等变量
（`.env` 不入库；不填时使用本地 mock provider，不影响其他功能）。

接口前缀 `/api/v1`，开发时前端由 CRA 的 proxy 转发到本服务。

**创建第一个管理员**：注册接口不开放 admin 角色，第一个管理员用 shell 建：

```bash
python manage.py shell -c "from user.models import User; from utils.jwt import encrypt_password; User.objects.create(username='admin1', password=encrypt_password('secret6'), nickname='admin', role='admin')"
```

之后可在 `/manage/accounts`（管理员登录前端）创建教师、管理员账号，
或用 CSV 批量导入学生名单。

## 目录结构

```text
├── app/           工程配置：settings.py（开发）、settings_prod.py（MySQL）、urls.py 总路由
├── user/          用户与账号：注册 / 登录、账号 CRUD、CSV 导入、审计日志
├── problem/       题库：题目与测试样例 CRUD
├── exam/          考场：考试管理（创建 / 组卷 / 名单 / 发布 / 撤回 / 归档）与学生作答闭环
├── agent/         AI 助教：分级会话、SSE 对话、工具调用与用量记录
├── practice/     自由练习：练习提交、判题任务与题目评论区
├── utils/         jwt.py（令牌 + login_required / role_required 装饰器）
├── nginx/         生产环境反向代理配置
├── docker-compose.yml / Dockerfile / Makefile
└── manage.py
```

每个应用内部分层：`models.py`（表）→ `controllers.py`（业务逻辑，返回 `(数据, 是否成功)`）
→ `views.py`（参数校验 + 组装响应）。接口路径写在各应用 `urls.py`，由 `app/urls.py` 汇总。

## 接口一览

| 接口 | 方法 | 角色 | 说明 |
| --- | --- | --- | --- |
| `/api/v1/register` | POST | — | 注册（用户名 / 密码 / 姓名 / 角色），成功即返回 JWT |
| `/api/v1/login` | PATCH | — | 登录，返回 JWT 与角色 |
| `/api/v1/logout` | PATCH | 已登录 | 登出（无状态，无操作） |
| `/api/v1/user` | GET | 已登录 | 当前登录用户信息 |
| `/api/v1/profile` | GET / PATCH | 已登录 | 个人中心：账号状态、使用概况、本人操作记录 / 修改姓名与邮箱 |
| `/api/v1/profile/password` | PATCH | 已登录 | 修改密码（校验原密码，新密码 6-64 位） |
| `/api/v1/users` | GET / POST | 管理员 | 账号列表（`role` / `keyword` 筛选）、创建账号 |
| `/api/v1/users/import` | POST | 管理员 | CSV 批量导入，逐行返回明细 |
| `/api/v1/users/:id` | GET / PATCH | 管理员 | 编辑账号（姓名 / 角色 / 邮箱 / 重置密码） |
| `/api/v1/audit` | GET | 管理员 | 最近 100 条审计日志 |
| `/api/v1/problems` | GET / POST | 教师 / 管理员 | 题库列表（`keyword` / `type` / `language` 筛选）、创建题目 |
| `/api/v1/problems/:id` | GET / PATCH / DELETE | 教师 / 管理员 | 题目详情、编辑（`samples` 缺省不改用例）、删除（级联删用例） |
| `/api/v1/exams` | GET / POST | 教师 / 管理员 | 考试列表（`status` 筛选）、创建考试（保存为草稿） |
| `/api/v1/exams/:id` | GET / PATCH / DELETE | 教师 / 管理员 | 考试详情、编辑（开始后冻结、归档后锁定）、删除（仅草稿） |
| `/api/v1/exams/:id/problems` | PUT | 教师 / 管理员 | 组卷：整体替换题目与分值，顺序即题序 |
| `/api/v1/exams/:id/candidates` | PUT | 教师 / 管理员 | 考生名单整体替换；空数组 = 全体学生可参加 |
| `/api/v1/exams/:id/publish · withdraw · archive` | POST | 教师 / 管理员 | 发布（校验时间 / 题目 / 名单）、撤回（仅开始前）、归档（仅结束后） |
| `/api/v1/exams/:id/submissions` | GET | 教师 / 管理员 | 本场考试提交记录（`problemId` 过滤，不含代码正文） |
| `/api/v1/my/exams` | GET | 学生 | 我的考试列表（含各场我的提交数） |
| `/api/v1/my/exams/:id` | GET | 学生 | 考试详情：题面 + 样例测试 + 初始代码（**不下发隐藏测试**） |
| `/api/v1/my/exams/:id/submissions` | GET | 学生 | 我在本场考试的提交记录 |
| `/api/v1/my/exams/:id/problems/:pid/submissions` | GET / POST | 学生 | 某题提交历史（含代码）/ 提交答卷（发布时段内、按题限次，异步判题） |
| `/api/v1/submissions/:id` | GET | 本人 / 教师 / 管理员 | 单条提交详情、得分与用例判定（隐藏用例不返回输入/期望/输出） |
| `/api/v1/practice/problems` | GET | 学生 | 开放自由练习的算法题列表 |
| `/api/v1/practice/problems/:id` | GET | 学生 | 题面 + 公开样例 + 初始代码（隐藏用例不下发） |
| `/api/v1/practice/problems/:id/submissions` | GET / POST | 学生 | 我的练习提交历史 / 提交代码（异步判题） |
| `/api/v1/practice/submissions/:id` | GET | 本人 | 单次练习提交的状态与逐用例结果 |
| `/api/v1/practice/problems/:id/comments` | GET / POST | 已登录 | 题目评论区：列表 / 发布（可附带代码、用 `parentId` 回复） |
| `/api/v1/practice/comments/:id` | DELETE | 作者 / 教师 / 管理员 | 删除评论（回复一并删除） |
| `/api/v1/agent/capabilities` | GET | 学生 | 本场考试的 AI 级别、可用工具与剩余额度（`closed` 返回 403） |
| `/api/v1/agent/sessions` | POST | 学生 | 创建或取回某题会话（每场考试每题一个） |
| `/api/v1/agent/sessions/:id/messages` | GET / POST | 学生 | 对话历史 / 发消息（SSE：delta、tool_call、change、usage、done） |
| `/api/v1/agent/sessions/:id/changes` | GET | 学生 / 教师 | 本题 AI 修改记录（含 diff） |
| `/api/v1/agent/changes/:id/revert` | POST | 学生 | 撤销一次 AI 修改 |
| `/api/v1/agent/workspace` | GET / PUT | 学生 | 三级模式的工作区读写（`expectedRevision` 乐观锁） |
| `/api/v1/exams/:id/agent/sessions` | GET | 教师 / 管理员 | 本场考试全部 AI 会话：每人 token、消息数、修改次数 |
| `/api/v1/exams/:id/agent/summary` | GET | 教师 / 管理员 | 按学生汇总 AI token 用量与修改次数 |
| `/api/v1/agent/sessions/:id/transcript` | GET | 本人 / 教师 | 单条会话的完整转录、工具调用与修改记录 |

另有 `/api/schema/swagger-ui/` 与 `/api/schema/redoc/` 在线接口文档（Django 后台登录后可看）。

## 认证与权限

- 登录成功下发 JWT（有效期 `JWT_EXPIRE_HOURS`，见 `app/settings.py`）。
  客户端把令牌**原样**放在 `Authorization` 头里，不带 `Bearer` 前缀。
- 密码用 scrypt 散列后落库（`utils/jwt.py: encrypt_password`）。
- 权限用装饰器声明：`@login_required`（任意已登录）、`@role_required(User.ROLE_ADMIN, ...)`
  （未登录 401，角色不符 403），函数视图与 APIView 方法都可用。
- 权限矩阵（与 SRS 一致）：学生只能考试答题；教师管考试与题库；管理员再加账号、审计。
  注册页只开放学生 / 教师，管理员由后台创建。

## 数据模型

- `user.User`：账号（username 唯一）、姓名、邮箱、角色（student / teacher / admin）、密码散列。
- `user.AuditLog`：操作人、动作（登录 / 注册 / 账号变更 / 题库变更等）、详情、时间；
  登录、注册与账号、题库操作均自动落库。
- `problem.Problem`：题面（Markdown）、题型（工程 / 算法）、语言、难度、初始代码、
  依赖镜像（预留字段，当前统一使用 `JUDGE_IMAGE`）、
  单用例时限（默认 2000ms）、内存上限（默认 256MB）、输出上限（默认 1024KB）、创建人。
- `problem.TestSample`：所属题目、名称、输入、期望输出、是否样例；
  **样例对学生可见，隐藏用例仅判分使用**，编辑题目时用例整体替换（≤100 条）。
- `exam.Exam`：考试名称、课程、开始 / 结束时间、时长、每题提交上限、AI 策略
  （limited / open / closed）、状态机 draft → published → archived、创建人；
  开考后配置冻结，归档需已结束。
- `exam.ExamProblem` / `exam.ExamCandidate`：组卷条目（题序 + 分值）与考生名单
  （多对多）；名单为空表示全体学生可参加。
- `exam.Submission`：学生提交（考试 / 题目 / 学生、代码、语言、状态）；
  异步判题回填 verdict / score / 通过数 / 耗时 / 内存 / 编译输出 / 需人工复核等字段。
- `exam.SubmissionCase`：单用例判定结果（样例名、是否样例、verdict、耗时、内存、摘要）；
  隐藏用例不保存实际输出与错误信息。
- `practice.PracticeSubmission`：自由练习提交（与考试提交独立），状态 / verdict / 通过数与逐用例结果。
- `practice.ProblemComment`：题目评论（作者、内容、可选附带代码与语言）。

## 自由练习

教师可在题库中勾选「开放自由练习」，学生端「自由练习」页只展示 `practice_enabled=True` 的算法题。
练习提交走与考试相同的 Docker 沙箱和 Celery 队列，但使用独立的 `PracticeSubmission`，
不占用考试次数、不计入成绩；结果接口对隐藏用例只返回判定与耗时，不含输入输出。

每道练习题有评论区，学生可以讨论思路并附带代码，也可以回复其他评论（两级展示，回复的回复归到顶层）。
评论按时间倒序返回，作者可删除自己的评论，教师 / 管理员可删除任意评论；删除顶层评论会一并删除回复。

## 判题（Celery + Redis + Docker）

提交接口只落库并立即返回 `pending`，由独立的 Celery worker 异步判题：

```text
POST 提交 → status=pending → judge_submission.delay(id)
          → worker 领取（status=judging）
          → Docker 一次性容器：编译 + 逐用例运行（禁网 / 限 CPU、内存、进程 / 只读根文件系统）
          → 写回 status=judged|failed、verdict、score、SubmissionCase
```

- 判全部用例（样例 + 隐藏），按通过比例给分：`score = round(题目分值 × 通过数 / 总数)`。
- 同一题多次提交取最高分展示（`myBestScore` / `bestScore`）。
- 判题失败（Docker 不可用、无测试用例等）标记 `failed` 且 `needs_review=True`，供教师人工复核。
- 隐藏用例只进入临时沙箱容器，结果接口只返回判定、耗时与内存，不返回输入/期望/实际输出。

### 本地启动判题

```bash
# 1) Redis：只绑定本机回环地址，并设置访问密码
#    严禁使用 -p 6379:6379（会暴露到 0.0.0.0，构成 Redis 未授权访问）
docker run -d --name aicoding-redis \
  -p 127.0.0.1:6379:6379 \
  -e REDIS_PASSWORD='请替换为强密码' \
  redis:7-alpine \
  sh -c 'exec redis-server --requirepass "$REDIS_PASSWORD"'

# 2) 判题镜像（在仓库根目录）
docker build -t aicoding-judge:latest -f backend/judge/Dockerfile backend/judge

# 3) worker（Windows 必须用 solo 池）
#    启动前设置带密码的 broker 地址：
#    PowerShell: $env:CELERY_BROKER_URL="redis://:请替换为强密码@127.0.0.1:6379/0"
cd backend
celery -A app worker --pool=solo -l info

# 4) 不经过 Celery，同步判一条（调试用）
python manage.py judge_once <submission_id> --force

# 5) Redis 故障或 worker 中断后的兜底
python manage.py judge_requeue
```

> **Redis 安全要求**：本地开发也必须只监听 `127.0.0.1` 并设置 `requirepass`；
> 生产 compose 中的 `redis` 仅存在于内部网络，不要为它添加 `ports` 映射。
> 验证：`docker exec aicoding-redis redis-cli ping` 应返回 `NOAUTH`，
> `docker exec aicoding-redis redis-cli -a '<密码>' ping` 应返回 `PONG`。

`CELERY_BROKER_URL`、`JUDGE_IMAGE`、`JUDGE_ENQUEUE_ENABLED` 等配置见 `app/settings.py` 的「判题服务」一节。

## 测试

```bash
python manage.py test user problem exam judge agent practice   # 含判题、AI 助教与自由练习测试
python manage.py test judge                     # 仅判题相关
manage.py check
```

判题集成测试（需要 Docker 与 `aicoding-judge` 镜像）：

```bash
JUDGE_INTEGRATION=1 python manage.py test judge.tests.JudgeTaskTests
```



### 工程题评分脚本

教师在题库选择「工程题」，填写任务和源码目录约定，上传公开和隐藏两份 Python 评分脚本。可另传两个附件。在线工作区模板预置每位学生的工程文件，课程资料包供下载。学生直接在工作台新建和编辑多文件，保存后的版本供公开试运行和正式提交使用。模板中非文本或超过 256 KB 的文件作为只读附件进入评测快照。公开脚本可下载。试运行不计入正式提交次数。隐藏脚本由独立评测容器运行，学生可以查看得分和通过情况。

每份脚本定义 `grade(project)`，返回评分项列表。每项包含 `name`、`points`、`max_points`，可带 `feedback`。分值使用整数，单项满分为 1–1000 分，每份脚本可返回 1–100 项。两份脚本的实得分之和除以满分之和，再乘本题分值。公开与隐藏权重由各自的满分之和决定。

```python
def grade(project):
    result = project.run(["python3", "src/main.py"], stdin="2 3\n")
    passed = result["status"] == 0 and result["output"].strip() == "5"
    return [{
        "name": "基础输入",
        "points": 10 if passed else 0,
        "max_points": 10,
        "feedback": "" if passed else "输出不符合要求",
    }]
```

`project.run` 在学生容器中运行命令，返回退出状态与输出。可用 `cwd` 指定相对源码子目录，`timeout` 指定 1–30 秒的运行时限。服务类题目可使用 `with project.start([...]):` 启动学生程序，参考对端经回环连接它。两份脚本分别使用全新的源码副本。评分脚本通过 `project.run` 和 `project.start` 执行学生代码，测试数据可放于 `project.private`（仅评分容器访问）或 `project.shared`（两端可访问）。

起始项目和提交包上限为 16 MB，单份评分脚本上限为 256 KB。更新此功能后执行数据库迁移并重建应用镜像。旧工程题可在题库重新编辑并上传两份评分脚本。

## Docker 部署

在装有 Docker 和 Compose 的 Linux 服务器上，从仓库根目录执行：

```bash
cd backend
umask 077
test -f .env || cp .env.example .env
nano .env
```

按 `.env.example` 的说明填写密钥和密码。每项用 `openssl rand -hex 32` 单独生成，实际配置保存在服务器的 `.env` 中。

```bash
docker compose config --quiet
docker compose --profile build build judge-base
docker compose up -d --build
docker compose ps -a
curl -I http://127.0.0.1:8000
```

- `migrate` 显示 `Exited (0)` 表示数据库迁移和 Django 静态文件收集完成。应用和判题服务在此之后启动。
- Nginx 托管前端并转发后端请求，默认监听宿主机的 `127.0.0.1:8000`。通过宿主机的加密反向代理提供域名访问时，按模板填写域名并启用安全 Cookie。上游反向代理需要保留请求的主机名和协议，并关闭流式响应缓冲。
- MySQL 使用新的 Docker 数据卷。若旧部署曾使用宿主机目录存放数据库，先备份现有数据，再单独导入。
- 判题服务通过 `/var/run/docker.sock` 请求宿主机启动一次性沙箱容器，部署时使用受信任的宿主机。

## 约定

- 迁移文件（`**/migrations/*.py`）与 `db.sqlite3` 被 .gitignore 忽略（课程模板约定），
  拉取代码后先 `makemigrations user problem exam agent practice` 再 `migrate`。
- 接口返回 JSON 的键用 camelCase（`userId`、`sampleCount`、`isSample`…），
  与前端 TypeScript 类型一一对应。
- 新增接口时：先在应用 `controllers.py` 写业务函数，`views.py` 只做校验与响应组装，
  并用 `@extend_schema`（drf-spectacular）补接口描述。
- 算法题创建 / 编辑时必须提供题目描述与至少一条测试用例（否则无法判题）；
  语言、难度、时限、内存有默认值，可只填标题 + 题面 + 用例。
  用例分为样例（`isSample=true`，学生可见）与隐藏用例（`isSample=false`，仅判分）。

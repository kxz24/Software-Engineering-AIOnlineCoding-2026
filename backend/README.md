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

python manage.py makemigrations user problem exam   # 迁移文件被 .gitignore 忽略，需各自本地生成
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

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
| `/api/v1/my/exams/:id/problems/:pid/submissions` | GET / POST | 学生 | 某题提交历史（含代码）/ 提交答卷（发布时段内、按题限次，只收卷待判定） |

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
- `user.AuditLog`：操作人、动作（login / register / account.* / problem.*）、详情、时间；
  登录、注册与账号、题库操作均自动落库。
- `problem.Problem`：题面（Markdown）、题型（工程 / 算法）、语言、难度、初始代码、依赖镜像、创建人。
- `problem.TestSample`：所属题目、名称、输入、期望输出、是否样例；
  **样例对学生可见，隐藏用例仅判分使用**，编辑题目时用例整体替换（≤100 条）。
- `exam.Exam`：考试名称、课程、开始 / 结束时间、时长、每题提交上限、AI 策略
  （limited / open / closed）、状态机 draft → published → archived、创建人；
  开考后配置冻结，归档需已结束。
- `exam.ExamProblem` / `exam.ExamCandidate`：组卷条目（题序 + 分值）与考生名单
  （多对多）；名单为空表示全体学生可参加。
- `exam.Submission`：学生提交（考试 / 题目 / 学生、代码、语言、状态 pending）；
  判题服务接入前只收卷存档。

## 测试

```bash
python manage.py test user problem exam   # 35 个用例：注册 / 登录 / RBAC / 导入 / 审计 / 题库 / 考场闭环
python manage.py check
```

## 部署（docker-compose）

```bash
docker compose up -d --build
```

拓扑：`nginx（宿主机 8000）→ app（gunicorn，settings_prod）→ mysql`。
`settings.py` 里的 `JWT_SECRET` 与 `settings_prod.py` 里的 MySQL 口令目前是课程模板的占位值，
正式部署前改为环境变量注入。
前端构建产物由 nginx 直接托管，`/api` 反向代理到 app 容器（见 `nginx/app.conf`）。

## 约定

- 迁移文件（`**/migrations/*.py`）与 `db.sqlite3` 被 .gitignore 忽略（课程模板约定），
  拉取代码后先 `makemigrations user problem exam` 再 `migrate`。
- 接口返回 JSON 的键用 camelCase（`userId`、`sampleCount`、`isSample`…），
  与前端 TypeScript 类型一一对应。
- 新增接口时：先在应用 `controllers.py` 写业务函数，`views.py` 只做校验与响应组装，
  并用 `@extend_schema`（drf-spectacular）补接口描述。

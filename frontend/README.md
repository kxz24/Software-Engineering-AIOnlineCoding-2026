# 前端（`frontend/`）

AI Coding 在线编程考试平台的前端，按 `docs/prototype/本地预览版/` 中的高保真原型实现。

## 技术栈

- TypeScript 3.9 + React 16（Create React App / react-scripts 3.4.3）
- react-router-dom 5 管理路由，`@reduxjs/toolkit` + react-redux 管理登录状态
- Monaco Editor 在线代码编辑（静态资源本地加载，不走 CDN）
- 样式为原型中提取的纯 CSS 设计系统（`src/styles/`），不引入组件库

## 启动

```bash
cd frontend
#建议使用conda
npm install
npm start          # http://localhost:3000，自动打开浏览器
npm run startwithoutbrowser   # http://localhost:3001，不自动打开
npm run build      # 生产构建，产物在 build/
npm test -- --watchAll=false  # 页面冒烟测试（src/pages.smoke.test.tsx）
```

开发服务器通过 `package.json` 里的 `proxy` 把 `/api/v1/*` 转发到 `http://127.0.0.1:8000`，
所以本地联调时先启动后端：

```bash
cd backend
python manage.py makemigrations user   # 迁移文件被 backend/.gitignore 忽略，需各自本地生成
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

> Node.js 18+。脚本里已带 `--openssl-legacy-provider`，用于兼容较新的 Node 版本。

Monaco Editor 的运行时资源不进仓库：`npm install` 时 `postinstall` 钩子
（`scripts/copy-monaco.js`）会把 `node_modules/monaco-editor/min/vs` 复制到
`public/monaco-vs`（已加入 .gitignore），页面加载与生产构建都使用这份本地资源。

## 目录结构

```text
src/
├── api/           后端接口（client.ts：注册 / 登录 / 登出 / 当前用户；urls.ts：接口与路由常量）
├── components/    公共组件（Brand、Icon、Toast、CodeEditor=Monaco 封装）
├── layouts/       两端外壳：StudentLayout（顶部导航）、TeacherLayout（侧边栏 + 顶栏）
├── mock/          演示数据（接口未就绪时页面从这里取数）
├── pages/         页面
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── student/   02 我的考试、03 考试须知、04 做题工作台、05 提交结果、06 成绩报告
│   └── teacher/   07 考试管理、08 创建考试、09 题目配置、10 监考中心
├── styles/        prototype.css（设计系统）、workbench.css（工作台，作用域 .wb-root）、app.css（布局自适应）
├── roles.ts       角色定义与角色首页
└── store.ts       Redux store（token + user）
```

## 路由

| 原型页 | 路由 | 角色 |
| --- | --- | --- |
| 01 登录 | `/login` | — |
| （原型外补充）注册 | `/register` | — |
| 02 我的考试 | `/exams` | 学生 |
| 03 考试须知 | `/exams/:examId/precheck` | 学生 |
| 04 做题工作台 | `/exams/:examId/workbench` | 学生 |
| 05 提交结果 | `/exams/:examId/result` | 学生 |
| 06 成绩报告 | `/exams/:examId/report` | 学生 |
| 07 考试管理 | `/manage` | 教师 / 管理员 |
| 08 创建考试 | `/manage/new` | 教师 / 管理员 |
| 09 题目配置 | `/manage/:examId/problems` | 教师 / 管理员 |
| 10 监考中心 | `/manage/:examId/proctor` | 教师 / 管理员 |

登录成功后按账号在后台记录的角色跳转：学生进 `/exams`，教师与管理员进 `/manage`。
注册成功即视为登录，同样按角色跳转；注册页开放「学生 / 教师」两种角色，管理员由后台分配。

## 做题工作台（04）

- 代码区为 Monaco Editor：Python / C / C++ / Java 等语言语法高亮，编辑器右上角
  可切换当前文件的高亮语言（默认按文件扩展名自动推断）
- 多文件标签共用一个编辑器实例，切换文件时保留各文件的撤销历史与光标位置
- 代码草稿按考试自动保存到浏览器 `localStorage`（约 0.8s 防抖），刷新页面不丢失；
  后端保存接口就绪后替换为服务端保存

## 演示模式（临时）

后端只有登录接口，本地库还需要先建表建号。为了方便只看界面，登录页底部在
**开发环境**下多了一个「以学生身份预览 / 以教师身份预览」入口（`src/demo.ts`），
它不请求后端，直接把内置账号写进本地存储，用于逐页对照原型。

正式联调 / 上线前删除：删掉 `src/demo.ts`、`LoginPage.tsx` 中的入口与 `App.tsx`
中对应的分支即可。

## 与后端的关系

目前后端提供四个接口：

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/register` | POST | 注册（用户名 / 密码 / 姓名 / 角色），成功即返回 JWT |
| `/api/v1/login` | PATCH | 登录，返回 JWT 与角色 |
| `/api/v1/logout` | PATCH | 登出（无状态，仅清本地令牌） |
| `/api/v1/user` | GET | 当前登录用户信息 |

令牌保存在 `localStorage`，请求时原样放在 `Authorization` 头里（不带 `Bearer` 前缀）。
其余页面（考试、题目、成绩、监考）的数据来自 `src/mock/`，接口就绪后把对应的
`mock` 引用替换成 `fetch` 调用即可，页面组件不需要改结构。

## 后续工作

- 教师端侧边栏的题库管理、成绩分析、考生名单、镜像与资源、系统设置尚未实现，入口保留但不可跳转。
- 工作台的运行测试 / 终端输出 / Agent 会话仍是演示数据，等待沙箱与 Agent 服务接入。

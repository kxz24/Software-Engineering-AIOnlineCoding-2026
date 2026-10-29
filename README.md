# AICoding 考试平台

> 清华大学软件学院 · 软件工程课程大作业 · 项目组 A10

面向 AI 编程课程的在线考试平台：为考生提供容器化编码环境与多轮对话式 AI 助教，为教师提供命题配置、过程监控与基于过程数据的评分报告。

## 小组信息

| 角色 | 成员 |
| --- | --- |
| Agent / 会议 / 项目管理 | 康祥桢 |
| 前端 | 石恒睿、李劲逸 |
| 后端 | 吕浩 |

指导教师：刘璘

## 目录结构

```text
.
├── frontend/   前端：TypeScript + React
├── backend/    后端：Python
├── agent/      AI 助教 Agent：LangChain
└── docs/       文档与原型
    ├── requirements/  需求规格说明书（SRS）源码与用户故事地图
    └── prototype/     墨刀高保真原型（HTML 源文件与预览图）
```

## 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | TypeScript、React |
| 后端 | Python |
| AI Agent | LangChain |
| 代码编辑 | Monaco Editor |
| 运行时隔离 | 容器化评测环境 |

## 文档

- 需求规格说明书：[docs/requirements/requirements_v2.tex](docs/requirements/requirements_v2.tex)（XeLaTeX + ctex 编译）
- 用户故事地图：[docs/requirements/storymap.png](docs/requirements/storymap.png)
- 产品原型说明：[docs/prototype/README.md](docs/prototype/README.md)
- 墨刀在线原型：<https://modao.cc/proto/FgnsjqSBtnggwtjPrLH0B5/sharing>

## 协作约定

- 主分支 `main` 保持可运行；个人开发在功能分支上进行，通过 Pull Request 合入。
- 分支命名：`feat/<模块>-<简述>`、`fix/<模块>-<简述>`、`docs/<简述>`。
- 提交信息遵循 Conventional Commits：`feat: ...` / `fix: ...` / `docs: ...` / `refactor: ...`。
- **不要提交 `.env`、密钥、数据库导出、`node_modules`、`__pycache__`**（已在 `.gitignore` 中忽略）。
- 依赖文件随代码一起提交：Python 用 `requirements.txt`，前端用 `package.json` + `package-lock.json`。

## 本地开发

> 各模块的具体启动方式在对应目录的 README 中维护，本文件只放全局约定。

- 后端 / Agent：建议 Python 3.11+，每个模块独立虚拟环境（`python -m venv .venv`）。
- 前端：Node.js 18+，包管理器统一使用 npm。
- 环境变量从 `.env.example` 复制为 `.env` 后填写，`.env` 不入库。

## 网络说明

国内网络直连 `github.com` 可能超时，需配置代理后使用：

```powershell
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

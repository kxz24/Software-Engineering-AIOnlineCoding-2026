# 工程题包（实验版）

教师在「题库管理 → 导入工程题 ZIP」上传一个 ZIP。平台只规定包的目录和评分结果协议，题目内容、初始文件、测试及评分公式由教师提供。上传后平台准备环境，并用教师的私有参考提交试跑评分器；页面显示准备结果。自检未通过的题目不能随试卷发布。

```text
project.json
public/
  README.md
  src/main.c
private/
  grade.py
  tests/...
  selfcheck/src/main.c
```

`public/` 下的 UTF-8 文本文件显示在学生的多文件工作区；学生提交时保存这些文件的快照。`private/` 只留在服务端，判题时才送入无网络的容器。老师应把依赖资源、测试和评分脚本放在 private 中；不要在 public 中放隐藏答案。

## 教师需要做什么

1. 把学生需要看到和编辑的 UTF-8 文件放在 `public/`，把测试及评分程序放在 `private/`。
2. 在 `private/selfcheck/` 放一份自己确认可用的参考提交，目录结构与公开文件一致。平台用它验证环境与评分器，但不会发给学生。
3. 在 `project.json` 写题面、评分命令和所需工具，然后上传 ZIP；等待题库显示「自检通过」再组卷。只需了解作业用到的工具，不需要写 Dockerfile。

普通题包的 `project.json` 示例：

```json
{
  "title": "工程题标题",
  "description": "Markdown 题面",
  "environment": {
    "systemPackages": ["gcc", "make"],
    "pythonPackages": []
  },
  "graderCommand": ["python3", "private/grade.py"],
  "selfCheckMinScore": 80,
  "maxScore": 100,
  "language": "c",
  "difficulty": "hard"
}
```

平台从固定的 Python 3.11 基础镜像安装所列 Debian 软件包与 Python 包，按依赖组合缓存镜像。Debian 包填写包名，Python 包可填写包名或 `包名==版本`；不能包含 shell 命令或 URL。C/C++ 编译器、Java 工具链等可通过 Debian 包安装；需要 Node 包、特定操作系统或复杂构建步骤时可用下面的高级入口。构建只在题目准备阶段发生，学生提交时不会重装依赖。`selfCheckMinScore` 是参考提交应达到的最低分；不填时默认为 1 分。`language` 是工程题的展示标签，可填任意不超过 16 字符的简短语言名；实际执行工具由环境和评分命令决定，编辑器按文件扩展名提供语法高亮，未知扩展名按纯文本显示。

对现成环境也保留兼容入口：可不写 `environment`，改写 `"runtime": "build-tools"`。此模式使用部署方提供的镜像，没有自动环境构建和参考提交自检。默认 `build-tools` 对应 `PROJECT_JUDGE_IMAGE`（默认 `aicoding-project-judge:latest`）。部署方构建通用工具镜像：

```sh
docker build -t aicoding-project-judge:latest -f backend/judge/ProjectDockerfile backend/judge
# 或在 backend/ 目录执行：docker compose --profile build build project-judge-base
```

特殊工具链的高级入口：教师可放 `private/Dockerfile`，必要的构建文件放 `private/build/`；此时不写 `environment` 或 `runtime`，仍须提供 `private/selfcheck/`。构建上下文只包含 Dockerfile 与 `private/build/`；参考提交和构建文件不会随判题包进入学生运行容器。镜像必须提供 `/bin/sh` 和 `python3`，因为平台通用 runner 依赖它们。教师可以选用所需系统和工具链；构建失败时，题库显示错误原因，教师修正后重新上传或重试。当前实验版经判题 worker 的 Docker daemon 构建，尚未部署独立构建服务或镜像审计。

部署方仍可通过 `PROJECT_JUDGE_RUNTIMES_JSON` 提供可复用的现成环境；管理员只维护基础镜像、Docker 服务、资源和网络策略，不需要逐题编写评分规则。

评分命令在容器工作目录运行，环境变量 `PROJECT_SUBMISSION` 指向学生文件目录，`PROJECT_PRIVATE` 指向教师私有文件目录，`PROJECT_RESULT` 指向需要写出的 JSON 文件。评分器应在 `PROJECT_RESULT` 写入：

```json
{
  "score": 72.5,
  "maxScore": 100,
  "needsReview": true,
  "items": [
    {"name": "公开检查", "score": 5, "maxScore": 5, "visible": true},
    {"name": "隐藏检查", "score": 2.5, "maxScore": 5, "visible": false}
  ]
}
```

平台按试卷中该题分值缩放 `score/maxScore`，并将 `needsReview` 标在提交记录。隐藏评分项的名称和反馈不会下发给学生。人工报告分可留为待复核；当前实验版只记录待复核状态，尚未提供人工补分界面。

平台限制：ZIP 压缩体积不超过 8 MB，解压总量不超过 32 MB，公开文本不超过 1 MB，文件数不超过 512，单次提交不超过 200 KB。路径穿越、符号链接和重复文件会在导入时拒绝。容器禁网、限资源且每次判题销毁；教师评分脚本仍属于受信任代码，只有教师/管理员能上传。

## 本地 Arch Lab 示例

用户提供的 `archlab-handout.tar` 带有版权声明，示范包仅在本机生成，不随本分支提交。它放入六个公开待实现文件，并将原 handout、分项评分器和转换脚本放在 private。在线示例题采用纯自动 100 分：Part A 20、Part B 30、Part C 50；不设报告项。原课程作业的 75 分自动测试加 25 分报告规则仍保留在本地评分器的 `course` 模式，供原作业核对。示范包路径见本次任务工作目录中的 `archlab-project-demo.zip`。

本机已构建上述 Docker 镜像，并使用真实无网络容器执行本地 Arch Lab 示范包与已完成的六文件快照，结果为 87.8/100、9 个自动评分项、无需人工复核，平均 CPE 8.41。教师页上传、学生工作台及提交的接口/构建测试已通过；完整浏览器交互流程尚未做自动化验证。

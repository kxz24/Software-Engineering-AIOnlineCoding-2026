# 工程题包（实验版）

教师在「题库管理 → 导入工程题 ZIP」上传一个 ZIP。平台只规定包的目录和评分结果协议，题目内容、初始文件、测试及评分公式由教师提供。

```text
project.json
public/
  README.md
  src/main.c
private/
  grade.py
  tests/...
```

`public/` 下的 UTF-8 文本文件显示在学生的多文件工作区；学生提交时保存这些文件的快照。`private/` 只留在服务端，判题时才送入无网络的容器。老师应把依赖资源、测试和评分脚本放在 private 中；不要在 public 中放隐藏答案。

`project.json` 的最小示例：

```json
{
  "title": "工程题标题",
  "description": "Markdown 题面",
  "runtime": "build-tools",
  "graderCommand": ["python3", "private/grade.py"],
  "maxScore": 100,
  "language": "c",
  "difficulty": "hard"
}
```

可用的 runtime 由部署方配置；目前 `build-tools` 对应 `PROJECT_JUDGE_IMAGE`（默认 `aicoding-project-judge:latest`）。教师无需写 Dockerfile，也不能通过题包指定任意镜像。部署方只需构建一次通用工具镜像：

```sh
docker build -t aicoding-project-judge:latest -f backend/judge/ProjectDockerfile backend/judge
# 或在 backend/ 目录执行：docker compose --profile build build project-judge-base
```

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

用户提供的 `archlab-handout.tar` 带有版权声明，示范包仅在本机生成，不随本分支提交。它放入六个公开待实现文件，并将原 handout、分项评分器和转换脚本放在 private。由平台通用 runner 在 WSL 中执行该包与已完成的六文件提交，得到自动分 65.85/75、平均 CPE 8.41，25 分报告项待人工评阅。示范包路径见本次任务工作目录中的 `archlab-project-demo.zip`。

本机已构建上述 Docker 镜像，并使用真实无网络容器执行本地 Arch Lab 示范包与已完成的六文件快照，返回 65.85/100、12 个分项和待人工复核标记。教师页上传、学生工作台及提交的接口/构建测试已通过；完整浏览器交互流程尚未做自动化验证。

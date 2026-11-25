# Arch Lab 工程题示例：教师如何用普通依赖清单上传

这个目录展示“教师提供题目与评分规则，平台准备环境并判题”的完整做法。示例把 Arch Lab 的 Part A、B、C 作为一次六文件提交，满分 100：Part A 20、Part B 30、Part C 50；不含报告分。当前平台代码没有 Arch Lab 专用判断。

## 为什么仓库里没有成品 ZIP

本机已生成并实测 `archlab-project-demo.zip`，但原始 Arch Lab handout 明确要求未经许可不得复制。成品 ZIP 包含 handout 内容和教师参考提交，因此被 `.gitignore` 排除，不会推送到公开仓库。生成器和本目录的评分脚本是独立编写的，可以随仓库分享。队友须从课程允许的渠道取得 handout，并使用自己有权使用的参考提交，在本地生成 ZIP。不要把含有 handout 或答案的 ZIP 加入 Git。

## 准备两份本地材料

1. 已解压的 `archlab-handout` 目录：至少有 `README.md` 和 `sim.tar`。本机现成路径示例：`F:\grade 2 study\software engineering\groupproject\archlab-work\archlab\archlab-handout`。
2. 教师参考提交目录，包含以下六个相对路径，要求是一份你认可的可用答案：

```text
PartA/sum.ys
PartA/rsum.ys
PartA/copy.ys
PartB/seq-full.hcl
PartC/ncopy.ys
PartC/pipe-full.hcl
```

本机用于实测的参考目录是 `F:\grade 2 study\software engineering\groupproject\archlab-work\archlab-submission`。该目录含参考答案，不提交到平台仓库。

## 一键生成 ZIP（PowerShell）

在平台仓库根目录运行；将下面两处输入路径改成你自己的：

```powershell
python .\examples\archlab\build_package.py `
  --handout "F:\grade 2 study\software engineering\groupproject\archlab-work\archlab\archlab-handout" `
  --reference "F:\grade 2 study\software engineering\groupproject\archlab-work\archlab-submission" `
  --output .\examples\archlab\archlab-project-demo.zip
```

上面每行末尾的反引号是 PowerShell 的续行符。也可以把命令写成一行。生成器会把六个学生可编辑文件和说明放入 `public/`，把模拟器 handout、评分器放入 `private/`，把参考提交放入 `private/selfcheck/`。ZIP 顶层直接是 `project.json`、`public/`、`private/`。

题包的 `project.json` 使用**方案一**，关键配置如下：

```json
{
  "environment": {
    "systemPackages": ["gcc", "g++", "make", "perl", "flex", "bison", "libfl-dev", "libc6-dev"]
  },
  "graderCommand": ["python3", "private/grade.py"],
  "selfCheckMinScore": 80,
  "maxScore": 100
}
```

教师只列出作业需要的 Debian 工具包；平台生成并缓存运行镜像。`private/grade_archlab.py` 是教师自定的评分逻辑，它在临时目录编译模拟器、运行正确性测试和性能基准，最后给出分项分数。

## 本地预检与网页上传

电脑须已启动 Docker，平台后端的 Python 依赖须可用。可在上传前从仓库根目录运行：

```powershell
python .\examples\archlab\verify_locally.py .\examples\archlab\archlab-project-demo.zip
```

此命令直接调用平台的题包解析、镜像构建和真实容器评分路径。首次需要下载基础镜像并安装工具，时间较长；同一依赖组合的镜像会复用。本机已验证的参考提交得到 `87.8/100`，高于 `80` 分自检门槛。更换参考答案后得分可不同，须以你自己的结果为准。

随后登录教师端，进入“题库管理 → 导入工程题 ZIP”，选择刚生成的 ZIP。题库会先显示“环境准备中”，通过后显示“环境自检通过；参考提交得 X/100 分”。把这道题加入试卷并发布，学生便能在工作台看到六个文件，修改后提交。平台运行教师评分器并按试卷中该题的分值折算。学生看不到 `private/`、参考提交和隐藏评分项名称。

## 遇到问题时

- 提示 ZIP 缺文件：检查 handout 目录、六个参考文件及 ZIP 顶层结构。
- 构建失败：检查 Docker、网络下载能力和 `systemPackages` 包名；题库会显示错误摘要。
- 自检低于 80：检查参考文件、评分器和测试预期。题包内容需要改时重新生成 ZIP 并导入；“重试自检”只对同一个已上传的包重新准备。
- 成绩与原课程不一致：本在线示例将原报告部分剔除，并改成自动测评 100 分；它不是原课程评分标准的逐项照搬。

平台接口及限制见[工程题上传与测评 v1](../../docs/工程题上传与测评_v1.md)，面向普通题目的指南见[教师导入工程题教程](../../docs/教师导入工程题教程.md)。

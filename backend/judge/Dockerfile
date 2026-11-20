# 判题沙箱基础镜像
#
# 一个镜像覆盖 Python / C / C++ / Java，runner 由 worker 在每次判题时
# 通过 tar 写入容器，镜像本身只需要解释器与编译器。
#
# 构建（在仓库根目录）：
#   docker build -t aicoding-judge:latest -f backend/judge/Dockerfile backend/judge

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        default-jdk-headless \
        libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# 沙箱运行时由 Docker 以 nobody + 只读根文件系统 + tmpfs /sandbox 启动，
# 这里只声明工作目录。
WORKDIR /sandbox

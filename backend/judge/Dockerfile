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
        make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyftpdlib==2.2.0

# 运行时使用低权限身份和只读根文件系统，工作目录由任务挂载。
WORKDIR /sandbox

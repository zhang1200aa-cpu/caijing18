# 使用官方 Python 3.8+ 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（如果需要）
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件到容器
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口（你的 Flask 应用使用的端口）
EXPOSE 5000

# 设置环境变量默认值
ENV TELEGRAM_BOT_TOKEN=""

# 启动应用
CMD ["python", "main.py"]

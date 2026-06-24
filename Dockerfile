FROM python:3.12-slim

WORKDIR /app

# Python deps
COPY requirements.txt .
# 使用 uv 安装依赖,利用 uv.lock 锁定版本
RUN pip install uv \
    && uv pip install --system --no-cache -r requirements.txt

# App
COPY . .

# 创建专用用户组与非 root 用户运行,降低容器逃逸风险
RUN groupadd -r appgroup && useradd -r -u 10001 -g appgroup appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appgroup /app \
    && chmod 755 /app/data
USER appuser

# Expose API port (default 8000)
EXPOSE 8000

# Health check — 不依赖 curl,改用 Python 标准库
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

# System deps
# - curl: healthcheck
# - build-essential, gfortran: pmdarima / arch 编译依赖
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Python deps — 先升 pip + setuptools + wheel,再装齐
COPY requirements.txt .
# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# App
COPY . .

# 创建非 root 用户运行,降低容器逃逸风险
RUN useradd -r -u 1000 -g users appuser \
    && mkdir -p /app/data \
    && chown -R appuser:users /app \
    && chmod 755 /app/data
USER appuser

# Expose API port (default 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

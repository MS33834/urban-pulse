# ── Stage 1: builder ──────────────────────────────────────────────────────
# 安装依赖到独立虚拟环境,运行镜像不携带 uv / 编译工具
FROM python:3.12-slim AS builder

WORKDIR /app

# 系统构建依赖(reportlab/openpyxl 等编译 wheel 可能需要)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# uv 提供远快于 pip 的依赖解析;--frozen 强制按 uv.lock 安装,不重新求解
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

# 把项目源码装进虚拟环境(让 backend.* / config.* 可被 import)
COPY . .
RUN uv sync --frozen --no-dev

# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# 创建专用用户组与非 root 用户运行,降低容器逃逸风险
RUN groupadd -r appgroup && useradd -r -u 10001 -g appgroup appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appgroup /app \
    && chmod 755 /app/data

# 从 builder 拷贝已装好的虚拟环境
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# 应用源码
COPY --from=builder --chown=appuser:appgroup /app /app

# 让 PATH 优先使用虚拟环境内的可执行文件
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# 健康检查 — 用 Python 标准库,不依赖 curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

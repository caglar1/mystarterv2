# syntax=docker/dockerfile:1
# Çok aşamalı imaj: derleme araçları (uv, Tailwind CLI) son imaja girmez.
#   docker build -t uygulama .
ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------------------
# 1) builder: bağımlılıklar + Tailwind derlemesi + collectstatic
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# Önce yalnızca bağımlılıklar (kod değişince bu katman önbellekten gelir)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

COPY . .
# Tailwind CLI sürümü ve sha256'sı apps/core/tailwind.py'de; burada tekrar yazılmaz.
RUN SECRET_KEY=yalnizca-derleme-icin /app/.venv/bin/python manage.py tailwind build \
 && SECRET_KEY=yalnizca-derleme-icin /app/.venv/bin/python manage.py collectstatic --noinput \
 && rm -rf .bin

# ---------------------------------------------------------------------------
# 2) runtime: sade Python + uygulama, root olmayan kullanıcı
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBUG=False
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home /app app \
 && mkdir -p /data/media \
 && chown -R app:app /data
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
USER app
EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "docker/healthcheck.py"]
ENTRYPOINT ["docker/entrypoint.sh"]
# gthread: uzun süren (SSE) istekler bir process'i değil bir thread'i meşgul eder.
# İnce ayar: GUNICORN_CMD_ARGS="--workers 4 --threads 8"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--worker-class", "gthread", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-"]

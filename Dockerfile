FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system blueberry \
    && useradd --system --gid blueberry --home-dir /app blueberry

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY scripts ./scripts

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && mkdir -p /app/storage/uploads /app/storage/petri_images /app/storage/micro_images \
    && chown -R blueberry:blueberry /app

USER blueberry

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "blueberry_microid.interfaces.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

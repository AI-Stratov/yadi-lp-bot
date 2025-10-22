FROM python:3.13-slim

RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

RUN mkdir -p /data && chown app:app /data

USER app

CMD ["uv", "run", "yadisk-lp"]

FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    procps libstdc++6 libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev && chown -R app:app /app

COPY src/ ./src/

RUN mkdir -p /data && chown app:app /data
USER app

CMD ["uv", "run", "yadi-lp"]

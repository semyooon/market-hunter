FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv venv && uv pip install --no-cache .

RUN useradd --create-home --uid 10001 appuser && mkdir -p /data && chown appuser:appuser /data
USER appuser
ENV MARKET_HUNTER_DATABASE_PATH=/data/market-hunter.db

CMD ["market-hunter-api"]

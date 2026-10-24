# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_SYSTEM_CERTS=true
# Optional CA bundle for a trusted enterprise egress proxy; never disable TLS.
RUN --mount=type=secret,id=custom_ca \
    if [ -f /run/secrets/custom_ca ]; then export SSL_CERT_FILE=/run/secrets/custom_ca; fi; \
    uv sync --frozen --no-dev --no-editable && useradd --uid 10001 --create-home researcher && mkdir /data && chown researcher:researcher /data
ENV PATH="/app/.venv/bin:$PATH" OPENPKLAB_DATA_DIR=/data MPLCONFIGDIR=/tmp/matplotlib
USER researcher
EXPOSE 8000
CMD ["openpklab", "serve", "--transport", "http", "--host", "0.0.0.0"]

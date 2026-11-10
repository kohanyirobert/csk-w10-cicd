FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/
WORKDIR /app
# Dependencies first: this layer is rebuilt only when the lock file changes, not on every code change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY app.py ./
EXPOSE 8080
# Python as PID 1 ignores SIGTERM, so every old Pod would hang 30 s in Terminating. It does stop on SIGINT.
STOPSIGNAL SIGINT
CMD ["/app/.venv/bin/python", "app.py"]

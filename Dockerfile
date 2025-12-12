# Builder stage: install build deps and Python packages
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libpq-dev gcc \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first to leverage Docker layer cache
COPY requirements.txt ./

# Upgrade pip and install into an isolated prefix to copy into final image
RUN python -m pip install --upgrade pip setuptools wheel \
	&& pip install --prefix=/install --no-cache-dir -r requirements.txt

# Copy source
COPY . /app

# Final stage: smaller runtime image
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PORT=8000

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local
# Copy application code
COPY --from=builder /app /app

# Ensure app files owned by non-root user and entrypoint executable
RUN chown -R app:app /app \
	&& chmod +x /app/entrypoint.sh || true

USER app

EXPOSE 8000

# Healthcheck (adjust path as your app exposes one)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD curl -f http://localhost:${PORT}/health || exit 1

# Entrypoint should exec to forward signals (ensure entrypoint.sh uses exec "$@")
ENTRYPOINT ["/app/entrypoint.sh"]

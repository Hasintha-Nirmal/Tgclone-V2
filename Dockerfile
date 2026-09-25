FROM python:3.11-slim

WORKDIR /app

# System deps first (cached unless they change)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps BEFORE copying app code
# This layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p sessions logs downloads

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Entrypoint runs as root to fix bind-mount dir permissions, then drops to appuser via gosu
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Default user (entrypoint overrides this by using gosu internally)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.7.1
RUN pip install poetry==${POETRY_VERSION}

# Configure Poetry to create venv in project
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=true \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy Poetry files
COPY pyproject.toml ./

# Generate lock file and install dependencies
RUN poetry lock --no-update 2>/dev/null || true && \
    poetry install --no-dev --no-root && \
    rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY app/ ./app/

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /entrypoint.sh
USER appuser

# Expose port
EXPOSE 8000

# Use entrypoint to ensure venv exists
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

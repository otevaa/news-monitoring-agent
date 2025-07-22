# Multi-stage Dockerfile for News Monitoring Agent with Ollama Support
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1 \
    OLLAMA_HOST=0.0.0.0:11434

# Install system dependencies and Ollama
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        supervisor \
        && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Install uv
RUN pip install uv #curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Remove development files
RUN rm -rf .git .gitignore .env.example deploy_production.sh start_production.sh

# Create supervisor configuration for multi-process management
RUN mkdir -p /etc/supervisor/conf.d
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root

[program:ollama]
command=ollama serve
user=appuser
autostart=true
autorestart=true
stderr_logfile=/var/log/ollama.err.log
stdout_logfile=/var/log/ollama.out.log
environment=HOME="/home/appuser",OLLAMA_HOST="0.0.0.0:11434"

[program:flask]
command=gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
directory=/app
user=appuser
autostart=false
autorestart=true
stderr_logfile=/var/log/flask.err.log
stdout_logfile=/var/log/flask.out.log
environment=HOME="/home/appuser"

EOF

# Create initialization script
RUN echo '#!/bin/bash\n\
echo "Starting Ollama service..."\n\
supervisorctl start ollama\n\
echo "Waiting for Ollama to be ready..."\n\
sleep 15\n\
echo "Pulling DeepSeek R1 model..."\n\
su - appuser -c "ollama pull deepseek-r1:1.5b" || echo "Failed to pull model, will retry later"\n\
echo "Starting Flask application..."\n\
supervisorctl start flask\n\
echo "All services started!"\n\
tail -f /dev/null' > /app/init.sh && chmod +x /app/init.sh

# Set secure permissions
RUN chown -R appuser:appuser /app /home/appuser && \
    chmod -R 755 /app && \
    chmod 600 /app/.env || true

# Expose ports
EXPOSE 5000 11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/ && curl -f http://localhost:11434/api/version || exit 1

# Start with supervisor managing all processes
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

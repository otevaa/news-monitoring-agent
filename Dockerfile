# Multi-stage Dockerfile for News Monitoring Agent with Ollama Support
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1 \
    OLLAMA_HOST=127.0.0.1:11434

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
RUN pip install uv 
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

# Create database directory
RUN mkdir -p /app/db

# Remove development files
RUN rm -rf .git .gitignore .env.example deploy_production.sh start_production.sh

# Create supervisor configuration for multi-process management
RUN mkdir -p /etc/supervisor/conf.d
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root
loglevel=info
logfile=/var/log/supervisor.log

[program:ollama]
command=ollama serve
user=appuser
priority=200
autostart=true
autorestart=true
stderr_logfile=/var/log/ollama.err.log
stdout_logfile=/var/log/ollama.out.log
environment=HOME="/home/appuser",OLLAMA_HOST="127.0.0.1:11434"

[program:flask]
command=/app/start_flask.sh
directory=/app
user=appuser
priority=100
autostart=true
autorestart=true
startsecs=15
stderr_logfile=/var/log/flask.err.log
stdout_logfile=/var/log/flask.out.log
environment=HOME="/home/appuser"

EOF

# Create initialization script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "=== NEWS MONITORING AGENT STARTUP ==="\n\
echo "Starting initialization..."\n\
echo "Current user: $(whoami)"\n\
echo "Working directory: $(pwd)"\n\
echo "App structure: $(ls -la /app | head -5)"\n\
\n\
# Start supervisor in background\n\
echo "Starting supervisor..."\n\
supervisord -c /etc/supervisor/conf.d/supervisord.conf &\n\
SUPERVISOR_PID=$!\n\
\n\
# Wait for Ollama to be ready\n\
echo "Waiting for Ollama to be ready..."\n\
for i in {1..30}; do\n\
  if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then\n\
    echo "✅ Ollama is ready!"\n\
    break\n\
  fi\n\
  echo "⏳ Waiting for Ollama... ($i/30)"\n\
  sleep 2\n\
done\n\
\n\
# Download model as appuser\n\
echo "⬇️  Downloading DeepSeek R1 model..."\n\
su appuser -c "ollama pull deepseek-r1:1.5b" || echo "⚠️ Model download failed, will retry later"\n\
\n\
# Wait for Flask to start\n\
echo "⏳ Waiting for Flask to be ready..."\n\
for i in {1..30}; do\n\
  if curl -s http://localhost:5000/health >/dev/null 2>&1; then\n\
    echo "✅ Flask is ready!"\n\
    break\n\
  fi\n\
  echo "⏳ Waiting for Flask... ($i/30)"\n\
  sleep 2\n\
done\n\
\n\
echo "🚀 Initialization complete!"\n\
echo "=== SERVICES STATUS ==="\n\
echo "Ollama: $(curl -s http://localhost:11434/api/version 2>/dev/null && echo "✅ OK" || echo "❌ FAIL")"\n\
echo "Flask: $(curl -s http://localhost:5000/health 2>/dev/null && echo "✅ OK" || echo "❌ FAIL")"\n\
echo "========================"\n\
\n\
# Wait for supervisor\n\
wait $SUPERVISOR_PID' > /app/init.sh && chmod +x /app/init.sh

# Set secure permissions
RUN chown -R appuser:appuser /app /home/appuser && \
    chmod -R 755 /app && \
    chmod 755 /app/db

# Create Flask startup wrapper  
RUN echo '#!/bin/bash\n\
set -e\n\
echo "=== FLASK STARTUP ==="\n\
echo "Starting Flask app..."\n\
echo "Current directory: $(pwd)"\n\
echo "Current user: $(whoami)"\n\
echo "App files: $(ls -la /app | head -5)"\n\
echo "Python packages: $(pip list | grep -E \"flask|gunicorn\" || echo \"No Flask/Gunicorn found\")"\n\
\n\
# Start Flask immediately - do not wait for Ollama\n\
echo "Starting Flask application on 0.0.0.0:5000"\n\
echo "Flask will be accessible on all interfaces"\n\
echo "Gunicorn configuration: --bind 0.0.0.0:5000 --workers 2 --timeout 120"\n\
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --log-level info --access-logfile - --error-logfile - app:app' > /app/start_flask.sh && chmod +x /app/start_flask.sh

# Expose ports (Flask as main service, Ollama internal only)
EXPOSE 5000

# Health check (Flask primary, Ollama secondary)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start with initialization script
CMD ["/app/init.sh"]

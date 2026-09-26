FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=index.py

# uid fixed so the container never runs as root. No chown of /app: the app only reads
# its own files, and a recursive chown over static/downloads (60 MB) would duplicate
# that whole layer.
RUN adduser --system --no-create-home --uid 10001 --group appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

USER appuser

EXPOSE 8000

# Shell form on purpose: the platform only injects PORT at runtime, and the exec form
# (JSON array) does not expand variables. `exec` makes gunicorn PID 1, so it receives
# SIGTERM directly and shuts down gracefully.
#
# gthread with a single worker: `sync` would block the whole process for the ~120s of
# each heatmap call, and more than one worker would multiply the ThreadPoolExecutors
# (heatmap prefetch and the AI pipeline) and the in-RAM cache, besides making the
# module-level globals in views/auth.py diverge.
#
# --timeout 300 is mandatory - the 30s default would kill every heatmap and every AI
# analysis. Do NOT add --max-requests: recycling the worker would abort AI analyses
# still running in the pipeline's executor.
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8000}" \
      --workers 1 --threads 6 --worker-class gthread \
      --timeout 300 --graceful-timeout 30 \
      --access-logfile - --error-logfile - index:app

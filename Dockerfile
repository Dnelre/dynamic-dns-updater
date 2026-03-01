FROM python:3.13.2-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY script/ .

RUN useradd --no-create-home appuser
USER appuser

HEALTHCHECK --interval=1m --timeout=5s --start-period=30s --retries=3 \
    CMD test -f /tmp/heartbeat && \
        [ $(($(date +%s) - $(cut -d. -f1 /tmp/heartbeat))) -lt 600 ]

CMD ["python", "dns-updater.py"]

FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY script/ .

HEALTHCHECK --interval=1m --timeout=5s \
  CMD test -f /tmp/heartbeat && \
      [ $(($(date +%s) - $(cut -d. -f1 /tmp/heartbeat))) -lt 600 ]

CMD ["python", "dns-updater.py"]

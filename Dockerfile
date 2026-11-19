FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    REELHOUSE_DATA_DIR=/data

COPY server.py ./server.py
COPY admin.html ./admin.html
COPY public ./public

RUN mkdir -p /data

EXPOSE 8080

CMD ["python", "/app/server.py"]

# Image pour un hébergement par conteneur (Fly.io, Railway, Render avec disque, VPS...)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Les données (base SQLite, justificatifs) vivent dans un volume persistant monté sur /data
ENV DATA_DIR=/data HTTPS=1 PORT=8080
VOLUME ["/data"]
EXPOSE 8080
CMD ["sh", "-c", "gunicorn --workers 1 --threads 4 --bind 0.0.0.0:${PORT} wsgi:application"]

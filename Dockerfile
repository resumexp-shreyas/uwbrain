FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sends traffic to $PORT. Model calls can take a while, so allow 120 s per request.
# Migrations run on start (safe to repeat).
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn uwbrain.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120"]

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    celery \
    redis \
    pillow \
    sqlalchemy \
    "psycopg[binary]" \
    exifread \
    piexif

COPY app ./app

CMD ["celery", "-A", "app.celery_app.celery_app", "worker", "--loglevel=info", "--pool=solo"]
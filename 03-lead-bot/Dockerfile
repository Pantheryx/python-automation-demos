FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# база заявок живёт в /data — примонтируйте сюда volume
ENV DB_PATH=/data/leads.db

CMD ["python", "bot.py"]

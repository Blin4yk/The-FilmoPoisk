FROM python:3.11

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src .

# Устанавливаем PYTHONPATH
ENV PYTHONPATH=/app

CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

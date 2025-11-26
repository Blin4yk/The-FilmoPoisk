FROM python:3.11

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src .

# Устанавливаем PYTHONPATH
ENV PYTHONPATH=/app

CMD ["fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "8000"]
FROM python:3.13

WORKDIR /app

COPY ../src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../src ./src

EXPOSE 8000
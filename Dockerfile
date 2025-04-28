FROM python:3.12.6-slim-bookworm-20240218

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
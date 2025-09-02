FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app.py /app/
COPY templates /app/templates
COPY static /app/static
RUN pip install --no-cache-dir flask waitress
EXPOSE 8080
CMD ["waitress-serve","--port=8080","app:app"]

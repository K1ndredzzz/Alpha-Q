# Build context: project root (one level above backend/).
# docker build -f backend/Dockerfile -t fuzhouxing/alpha-q-backend:latest .
FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" --uid 1000 appuser

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

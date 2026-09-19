FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip check

COPY . .

RUN useradd --uid 10001 --create-home appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=10 \
  CMD python -c "import httpx, sys; r = httpx.get('http://127.0.0.1:8000/health', timeout=5.0); sys.exit(0 if r.status_code == 200 else 1)" || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

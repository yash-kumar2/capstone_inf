FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip check

COPY . .

RUN useradd --uid 10002 --create-home appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=10 \
  CMD python -c "import httpx, sys; r = httpx.get('http://127.0.0.1:8501/_stcore/health', timeout=5.0); sys.exit(0 if r.status_code == 200 else 1)" || exit 1

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]

# Observatorio académico UNABot (Streamlit)
# Contexto de construcción: dashboard/
#   docker build -t unabot-dashboard dashboard
# En tiempo de ejecución se montan (ver docker-compose):
#   mcp_server/modelo_riesgo.json -> /app/modelo_riesgo.json
#   rag/eval                      -> /app/rag_eval
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin observatorio
COPY --chown=observatorio:observatorio . .
USER observatorio

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"

CMD ["streamlit", "run", "app.py", \
     "--server.port", "8501", \
     "--server.address", "0.0.0.0", \
     "--server.headless", "true", \
     "--browser.gatherUsageStats", "false"]

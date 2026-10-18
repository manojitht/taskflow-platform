FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN useradd --create-home --uid 10001 appuser
USER 10001
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/healthz')"
CMD ["sh", "-c", "python -m app.init_db && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]

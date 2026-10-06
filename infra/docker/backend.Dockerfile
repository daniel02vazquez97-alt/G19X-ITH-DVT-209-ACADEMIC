# Imagen `backend` (U7, `DT-095`): API V1 y procesos por lotes —migraciones, ingesta, forecast y
# recomendaciones— sobre la misma base (docs/12 §3.1). Contexto: raíz del repositorio.
#
# Dependencias: las fijadas en backend/pyproject.toml, grupos `db` y `api` (`DT-055`, `DT-064`); el
# grupo `test` no entra en la imagen. Imagen base fijada por versión exacta; el digest queda pendiente
# de resolverse contra el registro (`DT-095`).

FROM python:3.11.17-slim-trixie AS deps
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY backend/pyproject.toml ./
# pyproject.toml es la única fuente de versiones: se instalan `dependencies` y los grupos `db` y `api`.
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; o = p['optional-dependencies']; print('\n'.join(p['dependencies'] + o['db'] + o['api']))" > requirements.txt \
 && python -m venv /opt/venv \
 && /opt/venv/bin/pip install --requirement requirements.txt

FROM python:3.11.17-slim-trixie
ARG VERSION=0.0.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="inventory-backend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
RUN useradd --system --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin app
COPY --from=deps /opt/venv /opt/venv
WORKDIR /srv/backend
COPY backend/app ./app
COPY backend/db ./db
COPY infra/docker/serve_api.py ./serve_api.py
USER app
EXPOSE 8000
# Vida del proceso (`GET /health`, público y sin base de datos, `DT-066`).
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["python", "serve_api.py"]

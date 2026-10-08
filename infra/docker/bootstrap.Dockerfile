# Imagen `bootstrap` (U12, `DT-100`): el job manual que inicializa la base de `dev` en Azure en UNA ejecución y en
# orden (infra/docker/bootstrap.py): genera el dataset sintético 0.4.0, migra, carga, pronostica y recomienda.
#
# Por qué una imagen aparte: el job necesita a la vez el generador (data/synthetic, PyYAML) y los procesos del
# backend (psycopg); la imagen `backend` de la API no lleva el generador y la `dataset` no lleva el backend. Así la
# imagen de ejecución de la API sigue sin generador ni datos. El dataset NO va en la imagen: se genera en cada
# ejecución en un directorio temporal del contenedor. Contexto: raíz del repositorio (.dockerignore es una lista
# de permitidos). Misma base fijada por digest que `backend` y `dataset` (`DT-095`); sin secretos; usuario sin
# privilegios.

FROM python:3.11.17-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="inventory-bootstrap" \
      org.opencontainers.image.revision="${VCS_REF}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY backend/pyproject.toml backend/pyproject.toml
COPY data/synthetic/requirements.txt data/synthetic/requirements.txt
# Versiones fijadas: PyYAML del generador (`DT-024`) y el grupo `db` del backend (psycopg, `DT-055`).
RUN python -c "import tomllib; p = tomllib.load(open('backend/pyproject.toml', 'rb'))['project']; print('\n'.join(p['dependencies'] + p['optional-dependencies']['db']))" > /tmp/backend-requirements.txt \
 && pip install --requirement data/synthetic/requirements.txt --requirement /tmp/backend-requirements.txt \
 && rm /tmp/backend-requirements.txt \
 && useradd --system --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin bootstrap
COPY data/__init__.py data/__init__.py
COPY data/synthetic/__init__.py data/synthetic/__init__.py
COPY data/synthetic/config data/synthetic/config
COPY data/synthetic/generator data/synthetic/generator
COPY backend/app backend/app
COPY backend/db backend/db
COPY infra/docker/bootstrap.py bootstrap.py
USER bootstrap
# Proceso de una sola ejecución: lo vigila el job (código de salida), no un healthcheck.
HEALTHCHECK NONE
CMD ["python", "bootstrap.py"]

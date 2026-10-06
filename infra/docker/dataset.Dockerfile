# Imagen `dataset` (U7, `DT-095`): ejecuta el generador sintético 0.4.0 **sin modificarlo** para publicar
# el dataset en un volumen de Docker, de modo que un desarrollador nuevo no necesite Python en su máquina.
# El sistema sigue consumiendo el contrato del dataset (archivos publicados), no el código del generador.
# Contexto: raíz del repositorio. Dependencia: la de data/synthetic/requirements.txt (`DT-024`).

FROM python:3.11.17-slim-trixie
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="inventory-dataset" \
      org.opencontainers.image.revision="${VCS_REF}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY data/synthetic/requirements.txt data/synthetic/requirements.txt
RUN pip install --requirement data/synthetic/requirements.txt \
 && useradd --system --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin generator \
 && mkdir /data \
 && chown generator:generator /data
COPY data/__init__.py data/__init__.py
COPY data/synthetic/__init__.py data/synthetic/__init__.py
COPY data/synthetic/config data/synthetic/config
COPY data/synthetic/generator data/synthetic/generator
USER generator
# Proceso de una sola ejecución: no hay servicio que vigilar.
HEALTHCHECK NONE
# Si el volumen ya tiene un dataset publicado, se reutiliza; si no, se genera (unos 30 s).
CMD ["sh", "-c", "if [ -f /data/output/manifest.json ]; then echo 'dataset ya publicado en el volumen: se reutiliza'; else python -m data.synthetic.generator --output /data/output; fi && grep -m 1 dataset_version /data/output/manifest.json"]

# Imagen `frontend` (U7, `DT-095`): build de React con Node 24 LTS y servidor estático nginx que hace de
# proxy inverso de `/api` en el mismo origen (`DT-070` punto 23, docs/12 §3.1). Contexto: raíz del repositorio.
# Imágenes base fijadas por versión exacta y digest del índice multiplataforma (`DT-095`).

FROM node:24.21.0-trixie-slim@sha256:173f125896c3b47ddf056734c7ea789d04595a6a08769a8f78e0df642781fb66 AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# `build` = `tsc --noEmit && vite build` (package.json); lint y pruebas quedan para CI (U8).
RUN npm run build

FROM nginx:1.30.5-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
ARG VERSION=0.1.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="inventory-frontend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"
COPY infra/docker/nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
# Usuario sin privilegios de la imagen oficial (uid 101); escucha en 8080 y escribe solo en /tmp.
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=6 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
CMD ["nginx", "-g", "daemon off;"]

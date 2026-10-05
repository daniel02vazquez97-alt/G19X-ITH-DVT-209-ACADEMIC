# Interfaz React V1 (`frontend/`)

Interfaz de **solo lectura** del Motor Predictivo de Abastecimiento: Fase 7, decisiones en `DT-070`
(`docs/15-decisiones-tecnicas.md`) y diferencias de la V1 en `docs/08-frontend.md` §12. Consume la API V1
(`docs/07` §7) y **no recalcula nada**: muestra lo que la API entrega.

Estado: **F7a** — base, navegación por rol, autenticación local y cliente de API (US-070). Las vistas de
productos e inventario (F7b), recomendaciones y explicación (F7c) y predicciones e historial (F7d) son, por
ahora, páginas «En construcción» con su URL definitiva.

## Requisitos

- **Node.js 24 LTS** (≥ 24.15.0; referencia 24.21.0, ver `.nvmrc`) con **npm 11.19.0**.
- La API V1 en marcha en `127.0.0.1:8000` (`python -m app.api` desde `backend/`, con `APP_ENV=local`,
  `DATABASE_URL` y `DEV_AUTH_IDENTITIES`; ver `.env.example`).

## Uso

```bash
cd frontend
npm ci            # instala exactamente lo de package-lock.json
npm run dev       # http://127.0.0.1:5173
```

El servidor de desarrollo hace de **proxy**: el navegador llama a `/api/...` y Vite lo reenvía a
`http://127.0.0.1:8000`. La API no activa CORS (`DT-070` punto 23).

### Sesión

1. Pega en el formulario un token `dev-…` registrado en `DEV_AUTH_IDENTITIES` de la API local.
2. La interfaz lo valida con `GET /api/v1/me` y abre la sesión con los roles que devuelve.
3. El token se guarda **solo en memoria** (contexto de React): nunca en `localStorage`, `sessionStorage`,
   cookies, variables de build ni en el repositorio.

Consecuencias:

- **Al recargar la página hay que volver a entrar.**
- El _hot reload_ de Vite también puede cerrar la sesión: una edición que fuerza la recarga completa de la
  página (por ejemplo, de un módulo que no es un componente) borra la memoria y vuelve al formulario.
- «Cerrar sesión» descarta el token y la caché de datos.
- Un **401** de cualquier petición cierra la sesión y vuelve al formulario, sin cambiar la URL.
- Un **403** muestra «Sin permiso para ver esto» y **no** cierra la sesión.

Este mecanismo es la autenticación simulada de la Fase 7. `AuthProvider` lo aísla tras el puerto
`Authenticator` (`src/auth/authenticator.ts`) para que la Fase 8 (Entra ID) lo sustituya sin tocar las
vistas.

## Scripts

| Script                            | Qué hace                                                                                    |
| --------------------------------- | ------------------------------------------------------------------------------------------- |
| `npm run dev`                     | Servidor de desarrollo con proxy de `/api`                                                  |
| `npm run build`                   | Comprobación de tipos y build de producción en `dist/`                                      |
| `npm run typecheck`               | `tsc --noEmit`                                                                              |
| `npm run lint`                    | ESLint                                                                                      |
| `npm run format` / `format:check` | Prettier (escribir / comprobar)                                                             |
| `npm test`                        | Vitest + Testing Library (jsdom), una sola pasada                                           |
| `npm run gen:api`                 | Regenera `src/api/schema.gen.ts` desde `http://127.0.0.1:8000/openapi.json` (API en marcha) |

Lint, tipos, pruebas y build se ejecutan sin interacción. `src/api/schema.gen.ts` se versiona y se
regenera solo cuando cambia el contrato de la API; no se edita a mano.

## Estructura

```
src/
├── api/           cliente fino (/api, Bearer, errores), tipos del OpenAPI y useApiQuery
├── auth/          AuthProvider, puerto Authenticator, formulario de entrada
├── roles/         copia de la matriz de roles de docs/07 §7.2 y RoleGate
├── routes/        rutas estables y parámetros de lista en la URL
├── layout/        AppShell y navegación
├── pages/         inicio, «En construcción» y «no encontrada»
├── components/    ErrorState, EmptyState, LoadingSkeleton, NoticeBanner y tabla de errores
├── format/        presentación de cifras (DT-069) y fechas (es-MX, America/Mexico_City)
├── config/        locale y zona horaria
├── styles/        tokens de diseño y estilos globales (únicos puntos de corte)
├── architecture/  prueba de que el cliente no contiene fórmulas
└── test/          utilidades de prueba
```

## Reglas

- **Cero lógica de negocio** en el cliente: nada de cobertura, urgencia, riesgo ni punto de reorden, y
  ninguna conversión de cifras a `float` (`Number()`, `parseFloat`). Una prueba lo comprueba.
- Las cantidades llegan como texto y se muestran con la regla de `DT-069` (6 decimales
  `ROUND_HALF_EVEN`, sin ceros finales y **sin separador de miles**) o en su representación exacta.
- Fechas de calendario sin conversión de zona; marcas de tiempo de UTC a `America/Mexico_City`.
- Rutas, filtros, orden y paginación en la URL.
- Tokens de diseño en `src/styles/tokens.css`; puntos de corte solo en `src/styles/global.css`:
  tableta ≥ 48rem (768 px) y escritorio ≥ 64rem (1024 px).

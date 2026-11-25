# CU04 · Login con acceso según autorización

FastAPI + PostgreSQL + JWT (cookie HttpOnly) + Bcrypt · React + React Router.

## Estructura
```
backend/
  app/core/      config.py (entorno) · security.py (bcrypt + JWT) · rate_limit.py
  app/db/        session.py (engine, sesión por petición)
  app/models/    user.py (Usuario, Rol)
  app/schemas/   auth.py (validación de entrada/salida)
  app/services/  auth_service.py (lógica de login)
  app/api/       deps.py (get_current_user, require_roles) · routes/auth.py · routes/panels.py
  scripts/       crear_usuario.py · sql/schema.sql
frontend/src/
  api/client.js · context/AuthContext.jsx · components/RouteGuards.jsx
  pages/LoginPage.jsx · pages/Dashboards.jsx · utils/roles.js · App.jsx
```

## Medidas de seguridad
| Amenaza | Medida | Dónde |
|---|---|---|
| Inyección SQL | Consultas con ORM y parámetros enlazados; sin concatenar SQL; validación con Pydantic | `auth_service.py`, `schemas/auth.py` |
| Exposición de token (XSS) | JWT en cookie `HttpOnly`; no va en el JSON ni en localStorage | `routes/auth.py`, `api/client.js` |
| Robo de token en tránsito | Cookie `Secure` (HTTPS) y expiración corta (30 min) | `routes/auth.py`, `config.py` |
| CSRF | `SameSite=Lax`, CORS con orígenes explícitos | `routes/auth.py`, `main.py` |
| Fuga de datos en el JWT | Solo `sub`, `role`, `iat`, `exp`, `jti` | `security.py` |
| Alteración / `alg=none` | Algoritmo fijo y lista blanca al decodificar | `security.py` |
| Contraseñas filtradas | Bcrypt (12 rondas, salt por usuario) | `security.py` |
| Enumeración de cuentas | Mismo error y mismo tiempo para correo inexistente o clave errónea | `auth_service.py` |
| Fuerza bruta | 5 intentos por minuto por IP | `rate_limit.py` |
| Acceso cruzado entre roles | `require_roles` en el backend (real) y guards en React (UX) | `deps.py`, `RouteGuards.jsx` |
| Rol o estado desactualizado | Se consulta la BD en cada petición | `deps.py` |

## Pendientes recomendados para producción
Bloqueo temporal de cuenta tras N fallos, lista de revocación por `jti`, refresh tokens, HTTPS con HSTS, migraciones con Alembic y pruebas automatizadas.

---

# CU01 · Evaluación de riesgo fiscal (Dueño de MYPE)

## Backend (`/api/v1/evaluacion`, solo rol DUENO_MYPE)
| Método | Ruta | Función |
|---|---|---|
| GET | `/cuestionario` | Catálogo de preguntas (única fuente de verdad) |
| POST | `/` | Valida respuestas, llama al mock XGBoost, guarda y devuelve la evaluación |
| GET | `/historial` | Evaluaciones del usuario autenticado, de la más reciente a la más antigua |
| PATCH | `/{id}/recomendaciones/{rec_id}` | Guarda el avance del checklist |


## Frontend
```
src/features/evaluacion/
  SurveyForm.jsx · QuestionField.jsx · validaciones.js      (wizard por pasos)
  ResultsDashboard.jsx · RiskGauge.jsx · RiskHistoryChart.jsx
  RecommendationsChecklist.jsx · generarConstanciaPdf.js
src/pages/DashboardMype.jsx (estado pendiente/completado) · EvaluacionPage.jsx
src/api/evaluacionApi.js · src/hooks/useHistorial.js
```
Rutas: `/dashboard-mype` y `/dashboard-mype/evaluacion`.

---

# Modo Invitado (diagnóstico rápido para trabajo de campo)

| Pieza | Archivo |
|---|---|
| Migración (BD existente) | `backend/sql/002_modo_invitado.sql` (instalaciones nuevas: `evaluaciones.sql` ya lo incluye) |
| Modelo: `user_id` nullable + `is_guest` + CHECK | `backend/app/models/evaluacion.py` |
| Endpoint público `POST /api/v1/evaluacion/invitado` | `backend/app/api/routes/evaluacion.py` |
| Salida sin `id` ni `respuestas` | `backend/app/schemas/evaluacion.py` (`EvaluacionInvitadoOut`) |
| Límite por IP configurable | `GUEST_RATE_LIMIT` en `.env` (por defecto `30/hour`) |
| Botón en el login | `frontend/src/pages/LoginPage.jsx` + `.css` |
| Rutas públicas `/invitado/evaluacion` y `/invitado/resultado` | `frontend/src/App.jsx` |
| Wizard en modo invitado | `features/evaluacion/SurveyForm.jsx` (`modo="invitado"`) |
| Dashboard sin PDF ni historial | `features/evaluacion/ResultsDashboard.jsx` (`invitado`) |


Notas:
- El invitado no recibe cookie ni JWT. No se guarda IP, nombre ni correo.
- `GET /cuestionario` ahora es público (el invitado lo necesita; no contiene datos sensibles).
- En modo invitado no se guardan borradores y "Hacer otro diagnóstico" borra el resultado: el celular puede pasar de mano en mano.
- Detrás de un proxy/ngrok, configura la IP real (`X-Forwarded-For`) o el límite se aplicará a la IP del proxy.

---

# Auditoría: estados, notas internas y filtros del padrón (rol Auditor)

## Backend
| Pieza | Archivo |
|---|---|
| Campos `estado_auditoria`, `notas_auditor`, `auditado_por`, `auditado_en` | `backend/app/models/evaluacion.py` |
| Migración (BD existente; correr después de `002_modo_invitado.sql`) | `backend/sql/003_auditoria.sql` (instalaciones nuevas: `evaluaciones.sql` ya la incluye) |
| `GET /api/evaluaciones` y `PUT /api/evaluaciones/{id}/auditoria` | `backend/app/api/routes/auditoria.py` |
| Esquemas | `backend/app/schemas/auditoria.py` |

`GET /api/evaluaciones` — query params opcionales: `estado_auditoria` (`PENDIENTE` \| `EN_REVISION` \| `CERRADO`), `fecha_inicio`, `fecha_fin` (`YYYY-MM-DD`, inclusivas, calendario de Lima), `limit` (1–100, def. 20), `offset`. Responde `{items, total, limit, offset}`.

`PUT /api/evaluaciones/{id}/auditoria` — cuerpo `{estado_auditoria, notas_auditor}` (nota máx. 2000 caracteres; vacía => sin nota). Devuelve la evaluación actualizada. Códigos: 200, 401, 403, 404, 422.

- Solo el rol Auditor; Dueño de MYPE y Administrador reciben 403.
- `auditado_por` sale del token, nunca del cuerpo. Estado y notas **no** aparecen en las respuestas del Dueño de MYPE ni del invitado.
- El padrón y el `PUT` **excluyen las evaluaciones de invitados** (son anónimas).
- Estados con códigos estables; etiquetas ("En revisión") en el frontend (`utils/auditoria.js`).

## Frontend (`src/`)
```
pages/DashboardAuditor.jsx            hooks/usePadron.js        api/auditoriaApi.js
features/auditoria/FiltrosPadron.jsx  PadronLista.jsx  AuditoriaDrawer.jsx  DatosEvaluacion.jsx  EstadoBadge.jsx
```
El panel lateral tiene un espacio (`children`) para montar el gráfico SHAP existente: ver el comentario en `DashboardAuditor.jsx`.

---

# Panel del Auditor: filtros avanzados, comparativo sectorial y SHAP

## Migraciones (en orden)
`backend/sql/003_auditoria.sql` → `backend/sql/004_sector_y_filtros.sql` (columna `sector_economico`, relleno desde `respuestas`, índices por sector y probabilidad).

## Modelo SHAP
1. Copia tu modelo a `backend/models/modelo_ganador.joblib` (o define `MODELO_PATH`). No se incluye ningún modelo de ejemplo.
2. `MODELO_CLASE_RIESGO` indica qué clase explica SHAP (por defecto `"1"`).
3. Instala `shap`, `lightgbm`, `scikit-learn`, `pandas`, `joblib` **con las mismas versiones del entrenamiento** (`requirements.txt`). joblib usa pickle: carga solo archivos de confianza.
4. **Punto de integración:** `backend/app/services/features.py::construir_features` debe reproducir tu preprocesamiento. Es lo único que probablemente tengas que adaptar.
Si el modelo falta o falla, el endpoint responde 503/422/500 con mensajes controlados y el resto del panel sigue funcionando.

## Endpoints (rol AUDITOR; las evaluaciones de invitados responden 404)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/evaluaciones` | `estado_auditoria`, `sector_economico`, `probabilidad_min/max` (0–100 %), `fecha_inicio/fin`, `limit` (1–100), `offset` → `{items,total,limit,offset}` |
| PATCH | `/api/evaluaciones/{id}/auditoria` | Parcial: `estado_auditoria` y/o `notas_auditor` (≥1 campo). El `PUT` anterior se mantiene |
| GET | `/api/evaluaciones/{id}/comparativo-sectorial` | Probabilidad de la MYPE vs promedio de su sector y general (fracciones 0–1) |
| GET | `/api/evaluaciones/{id}/shap?max_display=12` | JSON: variable, etiqueta, valor, contribución SHAP, valor base y predicción |

## Frontend (`src/features/auditoria/`)
`PadronAuditor` (contenedor) · `FiltrosAvanzados` · `Paginacion` · `PadronLista` · `AuditoriaDrawer` (datos, `ComparativoSectorial`, `ShapWaterfallChart`, select de estado, textarea de notas) · hooks `usePadron`, `useCarga`.

**Colores SHAP:** verde = contribución positiva al riesgo, rojo = negativa (según el pedido; es lo contrario de la convención habitual). Se invierten intercambiando `SHAP_COLOR_POSITIVO/NEGATIVO` en `src/utils/auditoria.js`.
**Estado:** el código `EN_REVISION` se muestra como "En investigación".

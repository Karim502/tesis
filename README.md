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

## Puesta en marcha
```bash
# 1) Base de datos
createdb tesis_mype && psql -d tesis_mype -f backend/sql/schema.sql

# 2) Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # completa DATABASE_URL y JWT_SECRET_KEY
python -m scripts.crear_usuario          # crea un usuario por cada rol
uvicorn app.main:app --reload --port 8000

# 3) Frontend
cd ../frontend && cp .env.example .env && npm install && npm run dev
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

Archivos nuevos: `models/evaluacion.py`, `schemas/evaluacion.py`, `services/{cuestionario,modelo_riesgo,recomendaciones}.py`, `api/routes/evaluacion.py`, `sql/evaluaciones.sql`.

- `probabilidad` (0..1) es la probabilidad de incumplimiento; `score` (0..100) es el puntaje de cumplimiento (mayor = mejor).
- Para usar XGBoost real, reemplaza solo el cuerpo de `predecir_riesgo()` en `services/modelo_riesgo.py`.
- Para pasar de 3 a 16 preguntas, agrega entradas a `PREGUNTAS`; el wizard y la validación se adaptan solos.

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

## Puesta en marcha adicional
```bash
psql -d tesis_mype -f backend/sql/evaluaciones.sql
cd frontend && npm install && npm run dev      # ahora incluye Tailwind, Recharts y jsPDF
```

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

Consulta de la muestra: `SELECT is_guest, COUNT(*) FROM evaluaciones GROUP BY is_guest;`

Notas:
- El invitado no recibe cookie ni JWT. No se guarda IP, nombre ni correo.
- `GET /cuestionario` ahora es público (el invitado lo necesita; no contiene datos sensibles).
- En modo invitado no se guardan borradores y "Hacer otro diagnóstico" borra el resultado: el celular puede pasar de mano en mano.
- Detrás de un proxy/ngrok, configura la IP real (`X-Forwarded-For`) o el límite se aplicará a la IP del proxy.

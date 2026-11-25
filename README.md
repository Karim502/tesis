# Sistema de Evaluación de Riesgo Fiscal en MYPE con Explicabilidad SHAP

Plataforma web para el diagnóstico preventivo del riesgo de incumplimiento tributario en micro y pequeñas empresas (MYPE), con predicción basada en LightGBM, explicabilidad local mediante valores SHAP, revisión por auditores y trazabilidad MLOps.

## Arquitectura y Despliegue en Producción

| Capa | Tecnología | Entorno / Servicio |
|---|---|---|
| **Frontend (SPA)** | React 18 · Vite · React Router (`vercel.json` rewrites) | Vercel (`https://tesis-sepia.vercel.app`) |
| **Backend (API REST)** | FastAPI · SQLAlchemy · Pydantic · SlowAPI | Render (`https://tesis-backend-vp0v.onrender.com`) |
| **Base de Datos** | PostgreSQL | Neon |
| **Almacenamiento ML** | Artefactos `.joblib` (`modelo_v5.joblib` activo) | Supabase Storage (S3) |

### Estructura del repositorio
```text
backend/
  app/
    api/
      deps.py                  # get_current_user, require_roles (RBAC)
      routes/
        auth.py                # Login, logout, sesión actual
        evaluacion.py          # Cuestionario público y diagnóstico invitado/usuario
        auditoria.py           # Padrón, filtros, comparativo sectorial y SHAP
        admin.py               # Gestión de modelos MLOps y bitácora de auditoría
        analisis.py            # Analítica agregada
        panels.py              # Vistas de panel por rol
    core/                      # config.py, security.py (JWT/Bcrypt), csrf.py, rate_limit.py
    db/                        # session.py
    models/                    # user.py, evaluacion.py, auditoria / bitácora / modelos ML
    schemas/                   # Validación Pydantic de entrada y salida
    services/                  # cuestionario.py, modelo_riesgo.py, explicabilidad.py, recomendaciones.py
  sql/                         # Esquema base y migraciones (modo invitado, auditoría, sector)
  tests/                       # Suite automatizada con pytest
frontend/
  vercel.json                  # Rewrite SPA para evitar 404 al recargar rutas (F5)
  src/
    api/                       # client.js, evaluacionApi.js, auditoriaApi.js, adminApi.js
    context/AuthContext.jsx    # Persistencia de sesión vía cookie HttpOnly
    components/RouteGuards.jsx # Protección de rutas por rol en interfaz
    features/evaluacion/       # SurveyForm, ResultsDashboard, RiskGauge, RecommendationsChecklist
    features/auditoria/        # PadronAuditor, FiltrosAvanzados, AuditoriaDrawer, ShapWaterfallChart
    pages/                     # LoginPage, EvaluacionPage, DashboardAuditor, AdminPanel
```

---

## Seguridad y Control de Acceso

| Amenaza | Medida implementada | Ubicación |
|---|---|---|
| Exposición de token (XSS) | JWT emitido exclusivamente en cookie `HttpOnly` (sin `localStorage`) | `routes/auth.py`, `api/client.js` |
| Robo de sesión cross-origin | Cookie `Secure` + `SameSite=None` sobre HTTPS con expiración corta | `routes/auth.py`, `config.py` |
| Falsificación de peticiones (CSRF) | Validación estricta de cabecera `Origin` (`verificar_origen`) y CORS explícito | `core/csrf.py`, `main.py` |
| Inyección SQL | Consultas parametrizadas mediante ORM SQLAlchemy y esquemas Pydantic | `services/`, `schemas/` |
| Contraseñas débiles / filtradas | Hash Bcrypt (12 rondas con salt único) y respuestas uniformes ante fallos | `core/security.py`, `auth_service.py` |
| Fuerza bruta y abuso público | Rate limiting por IP (`slowapi`) en login y envío invitado (`GUEST_RATE_LIMIT`) | `core/rate_limit.py`, `evaluacion.py` |
| Escalada de privilegios | Validación RBAC en servidor (`require_roles`) + consulta activa en BD | `api/deps.py`, `RouteGuards.jsx` |
| Cabeceras HTTP inseguras | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy` y `HSTS` | `main.py` |

---

## Módulos Funcionales y Endpoints (`/api`)

### 1. Evaluación Pública — Invitado Anónimo (CU01)
Para proteger la privacidad del dueño de la MYPE y facilitar el levantamiento de datos en campo, el diagnóstico opera de forma **anónima y sin inicio de sesión**:
- No requiere cuenta ni emite JWT; se registra en BD con `is_guest = TRUE` y `user_id = NULL`.
- No almacena IP, nombre ni correo electrónico del encuestado.

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/health` | Público | Verificación de estado del servicio y despertar de instancia en Render |
| `GET` | `/api/evaluacion/cuestionario` | Público | Catálogo oficial de preguntas y opciones válidas |
| `POST` | `/api/evaluacion/invitado` | Público | Valida respuestas, predice riesgo con `modelo_v5.joblib` y genera recomendaciones |
| `POST` | `/api/evaluacion` | `DUENO_MYPE` | Registra evaluación vinculada a cuenta autenticada |
| `GET` | `/api/evaluacion/historial` | `DUENO_MYPE` | Lista evaluaciones propias del usuario autenticado |
| `PATCH` | `/api/evaluacion/{id}/recomendaciones/{rec_id}` | `DUENO_MYPE` | Actualiza avance de recomendaciones |

### 2. Panel del Auditor y Explicabilidad SHAP (CU02)
El padrón de auditoría integra tanto evaluaciones registradas como **Invitado Anónimo** (`outerjoin` en consulta SQL), permitiendo auditar el 100 % de la muestra recolectada.

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/evaluaciones` | `AUDITOR` | Padrón paginado con filtros por `estado_auditoria`, `sector_economico`, `probabilidad_min/max` y fechas |
| `PATCH` / `PUT` | `/api/evaluaciones/{id}/auditoria` | `AUDITOR` | Actualiza estado (`PENDIENTE`, `EN_REVISION` / *"En investigación"*, `CERRADO`) y `notas_auditor` |
| `GET` | `/api/evaluaciones/{id}/comparativo-sectorial` | `AUDITOR` | Compara la probabilidad de la MYPE frente al promedio de su sector y al promedio general |
| `GET` | `/api/evaluaciones/{id}/shap?max_display=12` | `AUDITOR` | Calcula valores SHAP locales desde `modelo_v5.joblib` (`base` hasta `f(x)`) |

- **Convención visual SHAP (`ShapWaterfallChart`):** verde indica contribución positiva (incrementa el riesgo fiscal) y rojo indica contribución negativa (reduce el riesgo fiscal).

### 3. Administración y Gobernanza MLOps (CU03)
Accesible en `/admin-panel` para el rol `ADMINISTRADOR`:
- **Gestión de versiones de modelos:** visualización de modelos almacenados en Supabase S3 (`modelo_v5.joblib` en estado `ACTIVO`, `modelo_v4.joblib` en `ARCHIVADO`).
- **Bitácora de auditoría:** registro trazable y filtrable de inicios de sesión y modificaciones realizadas por auditores.

---

## Ejecución Local y Pruebas

```bash
# Backend
cd backend
pytest -q
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
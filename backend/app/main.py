import logging
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import admin, analisis, auditoria, auth, evaluacion, panels
from app.core.config import settings
from app.core.csrf import verificar_origen
from app.core.rate_limit import limiter
from app.db.session import SessionLocal
from app.services.explicabilidad import precalentar
from app.services.modelos import marcar_huerfanos

logger = logging.getLogger(__name__)


def _limpiar_huerfanos_arranque() -> None:
    db = SessionLocal()
    try:
        marcar_huerfanos(db, todos=True)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Fallo al limpiar entrenamientos huérfanos en el arranque")
    finally:
        db.close()


def _precalentar_seguro() -> None:
    try:
        precalentar()
    except Exception:
        logger.exception("Fallo al precalentar el explicador SHAP en el arranque")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _limpiar_huerfanos_arranque()
    threading.Thread(
        target=_precalentar_seguro,
        daemon=True,
        name="precalentar-shap",
    ).start()
    yield


es_prod = settings.ENV == "prod"

app = FastAPI(
    title="Tesis MYPE - API",
    lifespan=lifespan,
    dependencies=[Depends(verificar_origen)],
    docs_url=None if es_prod else "/docs",
    redoc_url=None if es_prod else "/redoc",
    openapi_url=None if es_prod else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, _exc: Exception):
    logger.exception("Error interno no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "Error interno del servidor",
            }
        },
    )

@app.middleware("http")
async def agregar_headers_seguridad(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Error interno no controlado en %s %s", request.method, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "INTERNAL_ERROR",
                    "message": "Error interno del servidor",
                }
            },
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if es_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(evaluacion.router, prefix="/api")
app.include_router(auditoria.router, prefix="/api")
app.include_router(analisis.router, prefix="/api")
app.include_router(panels.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import analisis, auditoria, auth, evaluacion, panels
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.explicabilidad import precalentar

# Sin documentación pública en producción reduce la superficie de ataque (opcional).
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Carga el modelo SHAP en segundo plano: el servidor atiende de inmediato y la primera consulta no espera.
    threading.Thread(target=precalentar, daemon=True, name="precalentar-shap").start()
    yield


app = FastAPI(title="Tesis MYPE - API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS con orígenes EXPLÍCITOS (nunca "*" junto a credentials).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["Content-Type"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(panels.router, prefix="/api")
app.include_router(evaluacion.router, prefix="/api")
app.include_router(auditoria.router, prefix="/api")
app.include_router(analisis.router, prefix="/api")

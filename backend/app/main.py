from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import auth, evaluacion, panels
from app.core.config import settings
from app.core.rate_limit import limiter

# Sin documentación pública en producción reduce la superficie de ataque (opcional).
app = FastAPI(title="Tesis MYPE - API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS con orígenes EXPLÍCITOS (nunca "*" junto a credentials).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://tesis-sepia.vercel.app" 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(panels.router)
app.include_router(evaluacion.router)
"""Limitador de peticiones por IP (mitiga fuerza bruta y credential stuffing)."""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def obtener_ip_cliente(request: Request) -> str:
    """
    En producción (detrás del proxy de Render/Cloudflare), extrae la IP real del cliente
    para evitar que todos los usuarios compartan el mismo límite bajo la IP del proxy.
    """
    if settings.ENV == "prod":
        for header in ("cf-connecting-ip", "true-client-ip"):
            ip = request.headers.get(header)
            if ip and ip.strip():
                return ip.strip()
        xff = request.headers.get("x-forwarded-for")
        if xff:
            primera = xff.split(",")[0].strip()
            if primera:
                return primera
    return get_remote_address(request)


limiter = Limiter(key_func=obtener_ip_cliente)
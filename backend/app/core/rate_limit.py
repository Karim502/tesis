"""Limitador de peticiones por IP (mitiga fuerza bruta y credential stuffing)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

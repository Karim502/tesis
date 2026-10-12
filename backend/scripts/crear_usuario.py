"""Crea un usuario con contraseña hasheada.  Uso (desde /backend):  python -m scripts.crear_usuario"""
import getpass

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Rol, Usuario


def main() -> None:
    nombre = input("Nombre: ").strip()
    email = input("Correo: ").strip().lower()
    rol = Rol(input(f"Rol {[r.value for r in Rol]}: ").strip())
    password = getpass.getpass("Contraseña: ")  # no se muestra ni queda en el historial
    with SessionLocal() as db:
        db.add(Usuario(nombre=nombre, email=email, rol=rol, password_hash=hash_password(password)))
        db.commit()
    print("Usuario creado.")


if __name__ == "__main__":
    main()

"""Endpoints de ejemplo protegidos por rol (acceso cruzado => 403)."""
from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models.user import Rol, Usuario

router = APIRouter(tags=["paneles"])


@router.get("/mype/panel")
def panel_mype(user: Usuario = Depends(require_roles(Rol.DUENO_MYPE))):
    return {"mensaje": f"Aquí {user.nombre} registrará los datos de su negocio y responderá el cuestionario."}


@router.get("/auditor/panel")
def panel_auditor(user: Usuario = Depends(require_roles(Rol.AUDITOR))):
    return {"mensaje": "Evaluaciones de riesgo fiscal, modelos predictivos e interpretabilidad SHAP."}


@router.get("/admin/panel")
def panel_admin(user: Usuario = Depends(require_roles(Rol.ADMIN))):
    return {"mensaje": "Gestión de usuarios, asignación de roles, monitoreo de encuestas y configuración."}

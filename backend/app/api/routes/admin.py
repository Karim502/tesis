"""
Módulo del ADMINISTRADOR (supervisor técnico / MLOps).  Prefijo /api/admin.

Todo el router exige rol ADMIN en el servidor (los guards de React son solo comodidad):
  Eje A · Gestión de accesos de Auditores (CRUD)
  Eje B · Ciclo de vida del modelo: métricas, reentrenamiento en segundo plano, historial y activación/rollback
  Eje C · Bitácora de auditoría y health check
"""
import importlib.metadata as md
import logging
import os
import shutil
import time
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.api.routes.auditoria import FECHA_MAX, FECHA_MIN, _limites_utc
from app.core.config import settings
from app.core.csrf import verificar_origen
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit_log import Accion, AuditLog
from app.models.evaluacion import Evaluacion
from app.models.model_version import EstadoModelo, ModelVersion
from app.models.user import Rol, Usuario
from app.schemas.admin import (
    ActivacionOut, AuditorCreate, AuditoresPage, AuditorOut, AuditorPatch, HealthOut, LogsPage, ModelosOut,
    ModelVersionOut, ServicioHealth,
)
from app.services import entrenamiento, modelos
from app.services.bitacora import registrar
from app.services.explicabilidad import ModeloNoDisponible, cargar_modelo

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verificar_origen), Depends(get_current_admin_user)],
)


def _error(status_code: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code, detail={"code": code, "message": message, **extra})


# ════════════════════════════════════════════════════════ EJE A · AUDITORES
def _auditor_o_404(db: Session, auditor_id: int) -> Usuario:
    # Solo cuentas con rol AUDITOR: por este endpoint el admin no puede tocar a otros admins ni a dueños de MYPE.
    u = db.execute(select(Usuario).where(Usuario.id == auditor_id, Usuario.rol == Rol.AUDITOR)).scalar_one_or_none()
    if u is None:
        raise _error(404, "NOT_FOUND", "Auditor no encontrado")
    return u


def _auditor_out(db: Session, u: Usuario) -> AuditorOut:
    n = db.execute(select(func.count()).select_from(Evaluacion).where(Evaluacion.auditado_por == u.id)).scalar_one()
    return AuditorOut.model_validate(u).model_copy(update={"revisiones": n})


@router.get("/auditores", response_model=AuditoresPage)
def listar_auditores(
    q: str | None = Query(None, max_length=100, description="Busca en nombre y correo"),
    estado: str | None = Query(None, pattern="^(activo|suspendido)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    filtros = [Usuario.rol == Rol.AUDITOR]
    if q and q.strip():
        t = q.strip()
        filtros.append(Usuario.nombre.icontains(t, autoescape=True) | Usuario.email.icontains(t, autoescape=True))
    if estado:
        filtros.append(Usuario.activo.is_(estado == "activo"))

    total = db.execute(select(func.count()).select_from(Usuario).where(*filtros)).scalar_one()
    revisiones = (
        select(func.count()).select_from(Evaluacion).where(Evaluacion.auditado_por == Usuario.id).correlate(Usuario).scalar_subquery()
    )
    filas = db.execute(
        select(Usuario, revisiones).where(*filtros).order_by(Usuario.creado_en.desc(), Usuario.id.desc()).limit(limit).offset(offset)
    ).all()
    items = [AuditorOut.model_validate(u).model_copy(update={"revisiones": n}) for u, n in filas]
    return AuditoresPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/auditores", response_model=AuditorOut, status_code=status.HTTP_201_CREATED)
def crear_auditor(data: AuditorCreate, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(get_current_admin_user)):
    if db.execute(select(Usuario.id).where(Usuario.email == data.email)).first():
        raise _error(409, "EMAIL_TAKEN", "Ya existe una cuenta con ese correo")
    # El rol lo fija el SERVIDOR: nunca viene del cuerpo (no hay forma de crear un admin por esta ruta).
    nuevo = Usuario(nombre=data.nombre, email=data.email, rol=Rol.AUDITOR, password_hash=hash_password(data.password), activo=True)
    db.add(nuevo)
    try:
        db.flush()
        registrar(db, admin, Accion.AUDITOR_CREADO, recurso_tipo="usuario", recurso_id=nuevo.id,
                  detalle={"email": nuevo.email, "nombre": nuevo.nombre}, request=request, commit=False)
        db.commit()
    except IntegrityError:  # carrera: dos altas simultáneas con el mismo correo
        db.rollback()
        raise _error(409, "EMAIL_TAKEN", "Ya existe una cuenta con ese correo")
    db.refresh(nuevo)
    return _auditor_out(db, nuevo)


@router.patch("/auditores/{auditor_id}", response_model=AuditorOut)
def actualizar_auditor(
    auditor_id: int, data: AuditorPatch, request: Request,
    db: Session = Depends(get_db), admin: Usuario = Depends(get_current_admin_user),
):
    """Edita nombre, restablece contraseña o SUSPENDE/REACTIVA (`activo`). La suspensión corta la sesión en la siguiente petición."""
    u = _auditor_o_404(db, auditor_id)
    campos = []
    if "nombre" in data.model_fields_set and data.nombre is not None and data.nombre != u.nombre:
        u.nombre = data.nombre
        campos.append("nombre")
    if "password" in data.model_fields_set and data.password is not None:
        u.password_hash = hash_password(data.password)
        campos.append("password")  # solo el NOMBRE del campo; jamás el valor
    if "activo" in data.model_fields_set and data.activo is not None and data.activo != u.activo:
        u.activo = data.activo
        registrar(db, admin, Accion.AUDITOR_REACTIVADO if data.activo else Accion.AUDITOR_SUSPENDIDO,
                  recurso_tipo="usuario", recurso_id=u.id, detalle={"email": u.email}, request=request, commit=False)
    if campos:
        registrar(db, admin, Accion.AUDITOR_ACTUALIZADO, recurso_tipo="usuario", recurso_id=u.id,
                  detalle={"email": u.email, "campos": campos}, request=request, commit=False)
    db.commit()
    db.refresh(u)
    return _auditor_out(db, u)


@router.delete("/auditores/{auditor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_auditor(auditor_id: int, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(get_current_admin_user)):
    """
    Elimina la cuenta. Sus revisiones (evaluaciones.auditado_por) y su historial en la bitácora NO se pierden: las FK son
    ON DELETE SET NULL y la bitácora conserva el correo congelado. Para un bloqueo reversible usa `activo=false` (suspender).
    """
    u = _auditor_o_404(db, auditor_id)
    registrar(db, admin, Accion.AUDITOR_ELIMINADO, recurso_tipo="usuario", recurso_id=u.id,
              detalle={"email": u.email, "nombre": u.nombre}, request=request, commit=False)
    db.delete(u)
    db.commit()


# ════════════════════════════════════════════════════════ EJE B · MLOPS
@router.get("/modelos", response_model=ModelosOut)
def listar_modelos(db: Session = Depends(get_db)):
    """Modelo activo + historial (más reciente primero). El panel consulta esto cada pocos segundos mientras entrena."""
    modelos.marcar_huerfanos(db)
    versiones = db.execute(select(ModelVersion).order_by(ModelVersion.version.desc()).limit(100)).scalars().all()
    activo = next((v for v in versiones if v.estado == EstadoModelo.ACTIVO.value), None)
    return ModelosOut(
        activo=activo,
        versiones=versiones,
        entrenando=any(v.estado == EstadoModelo.ENTRENANDO.value for v in versiones),
        modelo_en_uso="version" if activo else "archivo_base",
    )


@router.post("/modelos/reentrenar", response_model=ModelVersionOut, status_code=status.HTTP_202_ACCEPTED)
def forzar_reentrenamiento(
    background_tasks: BackgroundTasks,
    request: Request,
    lote: UploadFile | None = File(None, description="CSV con el nuevo lote. Sin archivo se usa el dataset por defecto"),
    activar_si_mejora: bool = Form(False, description="Activar solo si su F1 supera al del modelo activo"),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin_user),
):
    """
    Lanza el entrenamiento y responde YA con 202: el trabajo sigue en segundo plano (BackgroundTasks) y el progreso se
    consulta en GET /admin/modelos. Las condiciones del lote se validan ANTES de encolar para dar error inmediato.
    """
    modelos.marcar_huerfanos(db)
    if db.execute(select(ModelVersion.id).where(ModelVersion.estado == EstadoModelo.ENTRENANDO.value)).first():
        raise _error(409, "TRAINING_IN_PROGRESS", "Ya hay un reentrenamiento en curso")

    contenido: bytes | None = None
    if lote is not None and lote.filename:
        maximo = settings.ENTRENAMIENTO_MAX_MB * 1024 * 1024
        contenido = lote.file.read(maximo + 1)  # nunca se lee más de maximo+1 bytes en memoria
        if len(contenido) > maximo:
            raise _error(413, "FILE_TOO_LARGE", f"El archivo supera {settings.ENTRENAMIENTO_MAX_MB} MB")
        nombre_archivo = os.path.basename(lote.filename)[:80]
        origen, fuente = f"lote subido: {nombre_archivo}", contenido
    else:
        fuente = entrenamiento.ruta_dataset_defecto()
        if not fuente.is_file():
            raise _error(422, "DATASET_NOT_AVAILABLE", "No hay dataset por defecto en el servidor: sube un lote CSV.")
        origen = "dataset por defecto del servidor"
    try:
        entrenamiento.cargar_lote(fuente)  # falla rápido, con un mensaje que el admin puede corregir
    except entrenamiento.DatosInvalidos as exc:
        raise _error(422, "INVALID_DATASET", str(exc))

    version = (db.execute(select(func.max(ModelVersion.version))).scalar_one() or 0) + 1
    fila = ModelVersion(
        version=version, archivo=f"modelo_v{version}.joblib", estado=EstadoModelo.ENTRENANDO.value,
        etapa="en cola", origen_datos=origen, iniciado_por=admin.id,
    )
    db.add(fila)
    try:
        db.flush()
        registrar(
            db, admin, Accion.MODELO_REENTRENAMIENTO,
            recurso_tipo="modelo", recurso_id=fila.id, request=request, commit=False,
            detalle={"version": version, "origen": origen, "activar_si_mejora": activar_si_mejora},
        )
        db.commit()
    except IntegrityError:  # otro admin lanzó uno en el mismo instante (índice único parcial)
        db.rollback()
        raise _error(409, "TRAINING_IN_PROGRESS", "Ya hay un reentrenamiento en curso")

    try:
        ruta = entrenamiento.guardar_lote_subido(contenido, version) if contenido is not None else fuente
    except OSError:
        log.exception("No se pudo guardar el lote subido para la versión v%s", version)
        fila.estado = EstadoModelo.FALLIDO.value
        fila.etapa = None
        fila.error = "No se pudo guardar el archivo del lote en el servidor"
        fila.finalizado_en = datetime.now(timezone.utc)
        db.commit()
        raise _error(500, "UPLOAD_SAVE_FAILED", "No se pudo guardar el archivo del lote en el servidor")

    background_tasks.add_task(entrenamiento.ejecutar_entrenamiento, fila.id, str(ruta), activar_si_mejora, admin.id)
    db.refresh(fila)
    return fila


@router.get("/modelos/{modelo_id}", response_model=ModelVersionOut)
def ver_modelo(modelo_id: int, db: Session = Depends(get_db)):
    modelos.marcar_huerfanos(db)
    v = db.get(ModelVersion, modelo_id)
    if v is None:
        raise _error(404, "NOT_FOUND", "Versión no encontrada")
    return v


@router.post("/modelos/{modelo_id}/activar", response_model=ActivacionOut)
def activar_modelo(modelo_id: int, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(get_current_admin_user)):
    """Promueve un CANDIDATO o vuelve a un ARCHIVADO (rollback). El anterior pasa a ARCHIVADO."""
    v = db.get(ModelVersion, modelo_id)
    if v is None:
        raise _error(404, "NOT_FOUND", "Versión no encontrada")
    anterior = modelos.version_activa(db)
    try:
        advertencias = modelos.activar(db, v, admin.id)
    except modelos.ActivacionInvalida as exc:
        db.rollback()
        raise _error(422, exc.code, exc.message)
    registrar(db, admin, Accion.MODELO_ACTIVADO, recurso_tipo="modelo", recurso_id=v.id, request=request, commit=False,
              detalle={"version": v.version, "desde_version": anterior.version if anterior and anterior.id != v.id else None})
    db.commit()
    db.refresh(v)
    return ActivacionOut(modelo=v, advertencias=advertencias)


# ════════════════════════════════════════════════════════ EJE C · LOGS Y HEALTH
@router.get("/logs", response_model=LogsPage)
def listar_logs(
    accion: str | None = Query(None, max_length=40),
    usuario: str | None = Query(None, max_length=100, description="Parte del correo del autor"),
    rol: Rol | None = None,
    recurso_tipo: str | None = Query(None, pattern="^(evaluacion|usuario|modelo)$"),
    recurso_id: int | None = Query(None, ge=1),
    fecha_inicio: date | None = Query(None, ge=FECHA_MIN, le=FECHA_MAX),
    fecha_fin: date | None = Query(None, ge=FECHA_MIN, le=FECHA_MAX),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if accion is not None and accion not in Accion.TODAS:
        raise _error(422, "INVALID_ACTION", "Acción desconocida")
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise _error(422, "INVALID_RANGE", "La fecha de inicio no puede ser posterior a la fecha fin")

    filtros = []
    if accion:
        filtros.append(AuditLog.accion == accion)
    if usuario and usuario.strip():
        filtros.append(AuditLog.usuario_email.icontains(usuario.strip(), autoescape=True))
    if rol:
        filtros.append(AuditLog.usuario_rol == rol.value)
    if recurso_tipo:
        filtros.append(AuditLog.recurso_tipo == recurso_tipo)
    if recurso_id:
        filtros.append(AuditLog.recurso_id == recurso_id)
    desde, hasta = _limites_utc(fecha_inicio, fecha_fin)
    if desde:
        filtros.append(AuditLog.creado_en >= desde)
    if hasta:
        filtros.append(AuditLog.creado_en < hasta)

    total = db.execute(select(func.count()).select_from(AuditLog).where(*filtros)).scalar_one()
    items = db.execute(
        select(AuditLog).where(*filtros).order_by(AuditLog.creado_en.desc(), AuditLog.id.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return LogsPage(items=items, total=total, limit=limit, offset=offset)


def _version_paquete(nombre: str) -> str:
    try:
        return md.version(nombre)
    except md.PackageNotFoundError:
        return "no instalado"


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)):
    """Estado de los servicios. Nunca devuelve rutas del servidor, cadenas de conexión ni trazas."""
    servicios: list[ServicioHealth] = [ServicioHealth(nombre="API", estado="ok", detalle="Respondiendo")]

    db_ok = True
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        servicios.append(ServicioHealth(nombre="Base de datos", estado="ok", detalle="Conexión correcta",
                                        latencia_ms=round((time.perf_counter() - t0) * 1000, 1)))
    except Exception:
        db_ok = False
        log.exception("Health: falla la base de datos")
        servicios.append(ServicioHealth(nombre="Base de datos", estado="error", detalle="No responde"))

    t0 = time.perf_counter()
    try:
        m = cargar_modelo()
        activo = modelos.version_activa(db) if db_ok else None
        estado_ver = (
            (f"versión {activo.version} activa" if activo else "archivo base (sin versión registrada)")
            if db_ok
            else "versión en BD no verificable"
        )
        servicios.append(ServicioHealth(
            nombre="Modelo", estado="ok", latencia_ms=round((time.perf_counter() - t0) * 1000, 1),
            detalle=f"{m.tipo} cargado · {estado_ver}",
        ))
    except ModeloNoDisponible as exc:
        servicios.append(ServicioHealth(
            nombre="Modelo", estado="advertencia",
            detalle=f"No disponible ({exc.motivo}): las predicciones y la explicabilidad SHAP responderán 503",
        ))
    except Exception:
        log.exception("Health: falla del modelo")
        servicios.append(ServicioHealth(nombre="Modelo", estado="error", detalle="Error inesperado al comprobar el modelo"))

    carpeta = modelos.carpeta_modelos()
    try:
        carpeta.mkdir(parents=True, exist_ok=True)  # aún no existe antes del primer entrenamiento: crearla es inofensivo
    except OSError:
        pass
    if carpeta.is_dir() and os.access(carpeta, os.W_OK):
        libre_mb = shutil.disk_usage(carpeta).free // (1024 * 1024)
        servicios.append(ServicioHealth(nombre="Almacenamiento de modelos", estado="ok" if libre_mb > 200 else "advertencia",
                                        detalle=f"Carpeta escribible · {libre_mb} MB libres"))
    else:
        servicios.append(ServicioHealth(nombre="Almacenamiento de modelos", estado="error",
                                        detalle="La carpeta de modelos no existe o no es escribible: no se podrá reentrenar"))

    if db_ok:
        en_curso = db.execute(
            select(ModelVersion.version).where(ModelVersion.estado == EstadoModelo.ENTRENANDO.value)
        ).scalars().first()
        detalle_entrenamiento = f"En curso (v{en_curso})" if en_curso else "Sin trabajos en curso"
        estado_entrenamiento = "ok"
    else:
        detalle_entrenamiento = "No verificable sin conexión a la base de datos"
        estado_entrenamiento = "advertencia"
    servicios.append(ServicioHealth(nombre="Entrenamiento", estado=estado_entrenamiento, detalle=detalle_entrenamiento))

    libs = {n: _version_paquete(n) for n in ("lightgbm", "shap", "scikit-learn", "pandas")}
    faltan = [n for n, v in libs.items() if v == "no instalado"]
    servicios.append(ServicioHealth(
        nombre="Librerías ML", estado="advertencia" if faltan else "ok",
        detalle=("Faltan: " + ", ".join(faltan)) if faltan else " · ".join(f"{n} {v}" for n, v in libs.items()),
    ))

    estados = {s.estado for s in servicios}
    general = "error" if "error" in estados else "advertencia" if "advertencia" in estados else "ok"
    return HealthOut(estado_general=general, revisado_en=datetime.now(timezone.utc), servicios=servicios)

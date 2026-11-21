"""Registro, inicio de sesión, administración de usuarios y contenidos, y parámetros."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import auth, telefono
from ..config import config
from ..db import sesion
from ..models import ROLES, TIPOS_GENERADOR, Contenido, Usuario, Zona
from .. import solicitudes as negocio_insignias
from ..solicitudes import puntos_de
from .rutas import _actor, actor_id

router = APIRouter(prefix="/api")


def _perfil(s, u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "rol": u.rol, "flujo": u.flujo, "piloto": u.piloto,
            "tipo_generador": u.tipo_generador, "direccion": u.direccion, "zona": u.zona,
            "puntos": puntos_de(s, u.id) if u.rol == "solicitante" else None}


def _exigir_admin(u: Usuario):
    if u.rol != "administrador":
        raise HTTPException(403, "Solo el administrador")


# --------------------------------------------------------------- autenticación
class Registro(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    telefono: str
    direccion: str = Field(min_length=3, max_length=255)
    zona: str
    tipo_generador: str
    clave: str = Field(min_length=6, max_length=128)
    acepta_tratamiento_datos: bool


class Login(BaseModel):
    telefono: str
    clave: str


@router.post("/auth/registro", status_code=201)
def registro(d: Registro):
    """Autoregistro de solicitantes. Queda fuera del piloto hasta que el administrador lo habilite (RN-08)."""
    if not d.acepta_tratamiento_datos:
        raise HTTPException(400, "Debes aceptar el tratamiento de datos")
    tel = telefono.normalizar(d.telefono)
    if not tel or d.tipo_generador not in TIPOS_GENERADOR:
        raise HTTPException(400, "Teléfono o tipo de generador inválido")
    try:
        with sesion() as s:
            if d.zona not in negocio_insignias.zonas_activas(s):
                raise HTTPException(400, "Elige tu zona")
            u = Usuario(nombre=d.nombre.strip(), telefono=tel, direccion=d.direccion.strip(), zona=d.zona,
                        rol="solicitante",
                        tipo_generador=d.tipo_generador, piloto=not config().modo_piloto,
                        clave_hash=auth.hash_clave(d.clave))
            s.add(u)
            s.flush()
            return {"token": auth.crear_token(u.id), "usuario": _perfil(s, u)}
    except IntegrityError as e:
        raise HTTPException(409, "Ese teléfono ya está registrado") from e


@router.post("/auth/login")
def login(d: Login):
    with sesion() as s:
        u = s.scalar(select(Usuario).where(Usuario.telefono == telefono.normalizar(d.telefono)))
        if not u or not u.activo or u.rol not in ROLES or not auth.verificar_clave(d.clave, u.clave_hash):
            raise HTTPException(401, "Teléfono o clave incorrectos")
        return {"token": auth.crear_token(u.id), "usuario": _perfil(s, u)}


@router.get("/auth/yo")
def yo(uid: int = Depends(actor_id)):
    with sesion() as s:
        return _perfil(s, _actor(s, uid))


# --------------------------------------------------------------- usuarios (administrador)
class NuevoUsuario(BaseModel):
    nombre: str
    telefono: str
    rol: str = "solicitante"
    direccion: str | None = None
    zona: str | None = None
    tipo_generador: str | None = None
    piloto: bool = False
    clave: str = Field(min_length=6)


class CambioUsuario(BaseModel):
    rol: str | None = None
    piloto: bool | None = None
    activo: bool | None = None


@router.get("/usuarios")
def listar_usuarios(uid: int = Depends(actor_id)):
    with sesion() as s:
        _exigir_admin(_actor(s, uid))
        return [{**_perfil(s, u), "telefono": u.telefono, "activo": u.activo}
                for u in s.scalars(select(Usuario).order_by(Usuario.id))]


@router.post("/usuarios", status_code=201)
def crear_usuario(d: NuevoUsuario, uid: int = Depends(actor_id)):
    tel = telefono.normalizar(d.telefono)
    if not tel or d.rol not in ROLES:
        raise HTTPException(400, "Teléfono o rol inválido")
    try:
        with sesion() as s:
            _exigir_admin(_actor(s, uid))
            u = Usuario(nombre=d.nombre, telefono=tel, rol=d.rol, direccion=d.direccion, zona=d.zona,
                        tipo_generador=d.tipo_generador, piloto=d.piloto, clave_hash=auth.hash_clave(d.clave))
            s.add(u)
            s.flush()
            return _perfil(s, u)
    except IntegrityError as e:
        raise HTTPException(409, "Ese teléfono ya está registrado") from e


@router.patch("/usuarios/{usuario_id}")
def cambiar_usuario(usuario_id: int, d: CambioUsuario, uid: int = Depends(actor_id)):
    with sesion() as s:
        _exigir_admin(_actor(s, uid))
        u = s.get(Usuario, usuario_id)
        if not u:
            raise HTTPException(404, "No existe")
        if d.rol is not None:
            if d.rol not in ROLES:
                raise HTTPException(400, "Rol inválido")
            u.rol = d.rol
        if d.piloto is not None:
            u.piloto = d.piloto
        if d.activo is not None:
            u.activo = d.activo
        return _perfil(s, u)


# --------------------------------------------------------------- zonas (administrador)
class ZonaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)


class CambioZona(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=60)
    activa: bool | None = None


def _zona(z: Zona) -> dict:
    return {"id": z.id, "nombre": z.nombre, "activa": z.activa}


@router.get("/zonas/todas")
def todas_las_zonas(uid: int = Depends(actor_id)):
    with sesion() as s:
        _exigir_admin(_actor(s, uid))
        return [_zona(z) for z in s.scalars(select(Zona).order_by(Zona.nombre))]


@router.post("/zonas", status_code=201)
def crear_zona(d: ZonaIn, uid: int = Depends(actor_id)):
    try:
        with sesion() as s:
            _exigir_admin(_actor(s, uid))
            z = Zona(nombre=d.nombre.strip())
            s.add(z)
            s.flush()
            return _zona(z)
    except IntegrityError as e:
        raise HTTPException(409, "Esa zona ya existe") from e


@router.patch("/zonas/{zona_id}")
def cambiar_zona(zona_id: int, d: CambioZona, uid: int = Depends(actor_id)):
    """Renombrar actualiza también usuarios, direcciones, solicitudes y personal de esa zona."""
    from sqlalchemy import update
    from ..models import DireccionUsuario, PersonalCampo, Solicitud
    try:
        with sesion() as s:
            _exigir_admin(_actor(s, uid))
            z = s.get(Zona, zona_id)
            if not z:
                raise HTTPException(404, "No existe")
            if d.nombre and d.nombre.strip() != z.nombre:
                viejo, nuevo = z.nombre, d.nombre.strip()
                for modelo in (Usuario, DireccionUsuario, Solicitud, PersonalCampo):
                    s.execute(update(modelo).where(modelo.zona == viejo).values(zona=nuevo))
                z.nombre = nuevo
            if d.activa is not None:
                z.activa = d.activa
            s.flush()
            return _zona(z)
    except IntegrityError as e:
        raise HTTPException(409, "Esa zona ya existe") from e


# --------------------------------------------------------------- contenidos (5.2)
class ContenidoIn(BaseModel):
    tipo: str = Field(pattern="^(tutorial|horario|ruta|huerta|general)$")
    titulo: str = Field(min_length=3, max_length=160)
    cuerpo: str = Field(min_length=3)
    palabras_clave: str = ""
    flujo: str | None = None
    activo: bool = True


def _cont(c: Contenido) -> dict:
    return {"id": c.id, "tipo": c.tipo, "titulo": c.titulo, "cuerpo": c.cuerpo,
            "palabras_clave": c.palabras_clave, "flujo": c.flujo, "activo": c.activo}


@router.get("/contenidos")
def contenidos():
    """Público: material educativo activo."""
    with sesion() as s:
        return [_cont(c) for c in s.scalars(select(Contenido).where(Contenido.activo.is_(True)).order_by(Contenido.id))]


@router.post("/contenidos", status_code=201)
def crear_contenido(d: ContenidoIn, uid: int = Depends(actor_id)):
    with sesion() as s:
        _exigir_admin(_actor(s, uid))
        c = Contenido(**d.model_dump())
        s.add(c)
        s.flush()
        return _cont(c)


@router.put("/contenidos/{contenido_id}")
def editar_contenido(contenido_id: int, d: ContenidoIn, uid: int = Depends(actor_id)):
    with sesion() as s:
        _exigir_admin(_actor(s, uid))
        c = s.get(Contenido, contenido_id)
        if not c:
            raise HTTPException(404, "No existe")
        for k, v in d.model_dump().items():
            setattr(c, k, v)
        return _cont(c)


@router.delete("/contenidos/{contenido_id}", status_code=204)
def borrar_contenido(contenido_id: int, uid: int = Depends(actor_id)):
    with sesion() as s:
        _exigir_admin(_actor(s, uid))
        c = s.get(Contenido, contenido_id)
        if c:
            s.delete(c)


# --------------------------------------------------------------- parámetros
@router.get("/parametros")
def parametros():
    """Regla de puntos vigente (RN-06), pública para que sea explicable."""
    cfg = config()
    return {"modo_piloto": cfg.modo_piloto, "puntos": {
        "base_por_recoleccion": cfg.puntos_base, "por_kg_organico": cfg.puntos_kg_organico,
        "por_kg_reciclable": cfg.puntos_kg_reciclable,
        "alcancia_sube_cada": negocio_insignias.PASO_ALCANCIA, "trinitaria_crece_cada": negocio_insignias.PASO_TRINITARIA,
        "formula": "base + kg x factor del flujo (redondeo hacia abajo)",
        "nota": "Valores de ejemplo, sujetos a validación de la Fundación Santo Domingo"}}

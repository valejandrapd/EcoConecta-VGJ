"""API del backend para la web (solicitante, coordinadores y administrador).

Autenticación: `Authorization: Bearer <token>` (ver /api/auth/login). Para integraciones internas
también se acepta `X-Service-Key` (SERVICE_API_KEY) + `X-Usuario-Id`. Cada ruta valida el perfil
(sección 5.1 del reto).
"""
import hmac
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import auth
from .. import solicitudes as negocio
from .. import telefono
from ..config import config
from ..db import sesion
from ..ia import cascada
from ..ia.modelo import IANoDisponible
from ..models import (COORDINADOR_DE_FLUJO, DIAS_SEMANA, FLUJO_DE_ROL, PERSONAL_DE_COORDINADOR, ROLES, TIPOS_PERSONAL, CasoCoordinacion,
                      DireccionUsuario, HistorialSolicitud, PersonalCampo, Solicitud, Usuario)
from ..whatsapp.mensajeria import purgar_vencidos


def actor_id(authorization: str = Header(""), x_service_key: str = Header(""),
             x_usuario_id: int | None = Header(None)) -> int:
    if authorization.startswith("Bearer "):
        try:
            return auth.leer_token(authorization.removeprefix("Bearer ").strip())
        except auth.TokenInvalido as e:
            raise HTTPException(401, "Sesión inválida o vencida") from e
    esperada = config().service_api_key
    if esperada and x_usuario_id and hmac.compare_digest(x_service_key, esperada):
        return x_usuario_id
    raise HTTPException(401, "Inicia sesión")


router = APIRouter(prefix="/api")


def _actor(s, x_usuario_id: int) -> Usuario:
    u = s.get(Usuario, x_usuario_id)
    if not u or not u.activo or u.rol not in ROLES:
        raise HTTPException(401, "Usuario no válido")
    return u


def _errores(fn):
    try:
        return fn()
    except negocio.SinPermiso as e:
        raise HTTPException(403, str(e)) from e
    except negocio.ErrorSolicitud as e:
        raise HTTPException(400 if "No existe" not in str(e) else 404, str(e)) from e


def _sol(sol: Solicitud, actor: Usuario) -> dict:
    d = {"codigo": sol.codigo, "flujo": sol.flujo, "tipo_generador": sol.tipo_generador, "estado": sol.estado,
         "observaciones": sol.observaciones, "disponibilidad": sol.disponibilidad, "tamano": sol.tamano,
         "dias_disponibles": sol.dias_disponibles.split(",") if sol.dias_disponibles else [],
         "hora_desde": sol.hora_desde, "hora_hasta": sol.hora_hasta, "bonificacion": sol.bonificacion,
         "fecha_programada": sol.fecha_programada, "hora_programada": sol.hora_programada,
         "zona": sol.zona,
         "reciclador": sol.reciclador.nombre_completo if sol.reciclador else None,
         "reciclador_id": sol.reciclador_id,
         "coordinador": sol.coordinador.nombre if sol.coordinador else None,
         "puntos": sol.recoleccion.puntos if sol.recoleccion else None, "creada_en": sol.creada_en}
    if negocio.puede_ver_contacto(actor, sol):  # RN-07
        d["contacto"] = {"nombre": sol.usuario.nombre, "telefono": sol.usuario.telefono, "direccion": sol.direccion,
                         "etiqueta": sol.direccion_etiqueta}
    return d


def _ver(s, codigo: str, actor: Usuario) -> Solicitud:
    sol = _errores(lambda: negocio.obtener(s, codigo))
    if not negocio.puede_ver_contacto(actor, sol) and actor.rol != "administrador":
        raise HTTPException(404, "No existe esa solicitud")
    return sol


# --------------------------------------------------------------- solicitante
class NuevaSolicitud(BaseModel):
    flujo: str
    tipo_generador: str | None = None
    direccion: str | None = None
    disponibilidad: str | None = None
    observaciones: str = ""
    tamano: str | None = None
    dias: list[str] | None = None
    hora_desde: time | None = None
    hora_hasta: time | None = None
    direccion_etiqueta: str | None = Field(None, max_length=60)
    bonificacion: str | None = None
    zona: str | None = None


@router.post("/solicitudes", status_code=201)
def crear_solicitud(d: NuevaSolicitud, uid: int = Depends(actor_id)):
    with sesion() as s:
        actor = _actor(s, uid)
        sol = _errores(lambda: negocio.crear(s, actor, d.flujo, tipo_generador=d.tipo_generador,
                                             observaciones=d.observaciones, direccion=d.direccion,
                                             disponibilidad=d.disponibilidad, tamano=d.tamano, dias=d.dias,
                                             hora_desde=d.hora_desde, hora_hasta=d.hora_hasta,
                                             direccion_etiqueta=d.direccion_etiqueta,
                                             bonificacion=d.bonificacion, zona=d.zona))
        return _sol(sol, actor)


@router.get("/solicitudes/{codigo}")
def ver_solicitud(codigo: str, uid: int = Depends(actor_id)):
    with sesion() as s:
        actor = _actor(s, uid)
        return _sol(_ver(s, codigo, actor), actor)


@router.get("/solicitudes/{codigo}/historial")
def historial(codigo: str, uid: int = Depends(actor_id)):
    with sesion() as s:
        sol = _ver(s, codigo, _actor(s, uid))
        filas = s.scalars(select(HistorialSolicitud).where(HistorialSolicitud.solicitud_id == sol.id)
                          .order_by(HistorialSolicitud.id)).all()
        return [{"de": h.estado_anterior, "a": h.estado_nuevo, "nota": h.nota, "en": h.creado_en} for h in filas]


@router.get("/mis-solicitudes")
def mis_solicitudes(uid: int = Depends(actor_id)):
    with sesion() as s:
        actor = _actor(s, uid)
        sols = s.scalars(select(Solicitud).where(Solicitud.usuario_id == actor.id).order_by(Solicitud.id.desc())).all()
        return {"puntos": negocio.puntos_de(s, actor.id), "insignias": negocio.insignias(s, actor.id),
                "solicitudes": [_sol(x, actor) for x in sols]}


@router.get("/mis-direcciones")
def mis_direcciones(uid: int = Depends(actor_id)):
    """Dirección principal y direcciones etiquetadas del solicitante (para el asistente)."""
    with sesion() as s:
        actor = _actor(s, uid)
        extra = s.scalars(select(DireccionUsuario).where(DireccionUsuario.usuario_id == actor.id)
                          .order_by(DireccionUsuario.etiqueta)).all()
        return {"principal": actor.direccion, "zona": actor.zona,
                "guardadas": [{"etiqueta": d.etiqueta, "direccion": d.direccion, "zona": d.zona} for d in extra]}


# --------------------------------------------------------------- coordinación
@router.get("/bandeja")
def bandeja(estado: str | None = None, uid: int = Depends(actor_id)):
    """Bandeja del coordinador: solo las solicitudes de SU colectivo (RN-01)."""
    with sesion() as s:
        actor = _actor(s, uid)
        if actor.rol not in COORDINADOR_DE_FLUJO.values() and actor.rol != "administrador":
            raise HTTPException(403, "Solo coordinadores")
        q = select(Solicitud)
        if actor.rol != "administrador":
            q = q.where(Solicitud.flujo == FLUJO_DE_ROL[actor.rol])
        if estado:
            q = q.where(Solicitud.estado == estado)
        sols = s.scalars(q.order_by(Solicitud.id.desc()).limit(300)).all()
        casos = s.scalars(select(CasoCoordinacion).where(
            CasoCoordinacion.estado == "abierto",
            CasoCoordinacion.flujo.in_([actor.flujo, "general"]) if actor.flujo else True)).all()
        return {"solicitudes": [_sol(x, actor) for x in sols],
                "casos_whatsapp": [{"id": c.id, "flujo": c.flujo, "motivo": c.motivo, "resumen": c.resumen,
                                    "usuario": c.usuario.nombre if c.usuario else None, "creado_en": c.creado_en}
                                   for c in casos]}


class Asignacion(BaseModel):
    reciclador_id: int
    fecha: date | None = None  # si vienen fecha y hora, asigna y programa en un paso
    hora: time | None = None


class Programacion(BaseModel):
    fecha: date
    hora: time


class RegistroRecoleccion(BaseModel):
    cantidad_kg: Decimal = Field(gt=0, le=10000)
    observaciones: str | None = None


class Cancelacion(BaseModel):
    motivo: str | None = None


def _accion(codigo, uid, fn):
    with sesion() as s:
        actor = _actor(s, uid)
        sol = _errores(lambda: negocio.obtener(s, codigo))
        _errores(lambda: fn(s, sol, actor))
        s.flush()
        s.refresh(sol)
        return _sol(sol, actor)


@router.post("/solicitudes/{codigo}/revisar")
def revisar(codigo: str, uid: int = Depends(actor_id)):
    return _accion(codigo, uid, lambda s, sol, a: negocio.revisar(s, sol, a))


@router.get("/solicitudes/{codigo}/opciones-asignacion")
def opciones_asignacion(codigo: str, uid: int = Depends(actor_id)):
    """Solo recicladores de la zona, con los días, horas y fechas que cruzan con lo que eligió el usuario."""
    with sesion() as s:
        actor = _actor(s, uid)
        sol = _errores(lambda: negocio.obtener(s, codigo))
        _errores(lambda: negocio._exigir_coordinador(actor, sol))
        return [{"id": o["reciclador"].id, "nombre": o["reciclador"].nombre_completo, "zona": o["reciclador"].zona,
                 "dias": o["dias"], "desde": o["desde"], "hasta": o["hasta"], "fechas": o["fechas"]}
                for o in negocio.opciones_asignacion(s, sol)]


def _asignar(s, sol, a, d: Asignacion):
    negocio.asignar(s, sol, a, d.reciclador_id)
    if d.fecha and d.hora:
        negocio.programar(s, sol, a, d.fecha, d.hora)


@router.post("/solicitudes/{codigo}/asignar")
def asignar(codigo: str, d: Asignacion, uid: int = Depends(actor_id)):
    return _accion(codigo, uid, lambda s, sol, a: _asignar(s, sol, a, d))


@router.post("/solicitudes/{codigo}/programar")
def programar(codigo: str, d: Programacion, uid: int = Depends(actor_id)):
    return _accion(codigo, uid, lambda s, sol, a: negocio.programar(s, sol, a, d.fecha, d.hora))


@router.post("/solicitudes/{codigo}/recoleccion")
def recoleccion(codigo: str, d: RegistroRecoleccion, uid: int = Depends(actor_id)):
    return _accion(codigo, uid,
                   lambda s, sol, a: negocio.registrar_recoleccion(s, sol, a, d.cantidad_kg, d.observaciones))


@router.post("/solicitudes/{codigo}/cancelar")
def cancelar(codigo: str, d: Cancelacion, uid: int = Depends(actor_id)):
    return _accion(codigo, uid, lambda s, sol, a: negocio.cancelar(s, sol, a, d.motivo))


# --------------------------------------------------------------- personal de campo (sin cuenta)
def _exigir_coordinacion(actor: Usuario):
    if actor.rol not in COORDINADOR_DE_FLUJO.values() and actor.rol != "administrador":
        raise HTTPException(403, "Solo coordinadores o administrador")


def _personal(p: PersonalCampo) -> dict:
    return {"id": p.id, "tipo": p.tipo, "nombre": p.nombre, "apellido": p.apellido, "zona": p.zona,
            "dias": p.dias, "hora_desde": p.hora_desde, "hora_hasta": p.hora_hasta, "activo": p.activo}


class NuevoPersonal(BaseModel):
    tipo: str
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    zona: str | None = None
    dias: list[str] = Field(min_length=1)
    hora_desde: time
    hora_hasta: time


def _validar_personal(s, d: NuevoPersonal):
    if d.tipo not in TIPOS_PERSONAL:
        raise HTTPException(400, "tipo debe ser 'reciclador' o 'voluntario_huerta'")
    if d.tipo == "reciclador" and d.zona not in negocio.zonas_activas(s):
        raise HTTPException(400, "Elige la zona del reciclador")
    if any(x not in DIAS_SEMANA for x in d.dias):
        raise HTTPException(400, "Día inválido")
    if d.hora_desde >= d.hora_hasta:
        raise HTTPException(400, "La hora de inicio debe ser anterior a la de fin")


def _exigir_tipo_propio(actor: Usuario, tipo: str):
    """La coordinación de reciclaje gestiona recicladores; la de huerta, voluntarios de huerta."""
    if actor.rol != "administrador" and PERSONAL_DE_COORDINADOR.get(actor.rol) != tipo:
        raise HTTPException(403, "Tu coordinación no gestiona ese tipo de personal")


@router.get("/personal")
def listar_personal(tipo: str | None = None, uid: int = Depends(actor_id)):
    """Personal que gestiona el actor (el administrador ve todo)."""
    with sesion() as s:
        actor = _actor(s, uid)
        _exigir_coordinacion(actor)
        q = select(PersonalCampo).order_by(PersonalCampo.tipo, PersonalCampo.nombre)
        if actor.rol != "administrador":
            q = q.where(PersonalCampo.tipo == PERSONAL_DE_COORDINADOR[actor.rol])
        if tipo:
            q = q.where(PersonalCampo.tipo == tipo)
        return [_personal(p) for p in s.scalars(q)]


@router.post("/personal", status_code=201)
def crear_personal(d: NuevoPersonal, uid: int = Depends(actor_id)):
    """Integrar un reciclador (con zona) o un voluntario de huerta. No reciben usuario ni clave."""
    with sesion() as s:
        actor = _actor(s, uid)
        _exigir_coordinacion(actor)
        _validar_personal(s, d)
        _exigir_tipo_propio(actor, d.tipo)
        p = PersonalCampo(tipo=d.tipo, nombre=d.nombre.strip(), apellido=d.apellido.strip(),
                          zona=d.zona if d.tipo == "reciclador" else None,
                          dias_servicio=",".join(x for x in DIAS_SEMANA if x in d.dias),
                          hora_desde=d.hora_desde, hora_hasta=d.hora_hasta, creado_por_id=actor.id)
        s.add(p)
        s.flush()
        return _personal(p)


class CambioPersonal(BaseModel):
    activo: bool


@router.patch("/personal/{personal_id}")
def cambiar_personal(personal_id: int, d: CambioPersonal, uid: int = Depends(actor_id)):
    with sesion() as s:
        actor = _actor(s, uid)
        _exigir_coordinacion(actor)
        p = s.get(PersonalCampo, personal_id)
        if not p:
            raise HTTPException(404, "No existe")
        _exigir_tipo_propio(actor, p.tipo)
        p.activo = d.activo
        return _personal(p)


@router.get("/contacto")
def contacto():
    """Datos públicos de contacto: el número del bot para el botón "Escríbenos por WhatsApp"."""
    return {"whatsapp": config().whatsapp_numero_publico or None}


@router.get("/zonas")
def zonas():
    """Zonas activas (públicas: se usan en el registro)."""
    with sesion() as s:
        return negocio.zonas_activas(s)


@router.get("/resumen")
def resumen(desde: date | None = None, hasta: date | None = None, uid: int = Depends(actor_id)):
    """Resumen básico por flujo, estado y periodo (sección 5.6)."""
    with sesion() as s:
        actor = _actor(s, uid)
        if actor.rol not in COORDINADOR_DE_FLUJO.values() and actor.rol != "administrador":
            raise HTTPException(403, "Solo coordinadores o administrador")
        q = select(Solicitud.flujo, Solicitud.estado, func.count()).group_by(Solicitud.flujo, Solicitud.estado)
        if actor.rol != "administrador":
            q = q.where(Solicitud.flujo == actor.flujo)
        if desde:
            q = q.where(Solicitud.creada_en >= datetime.combine(desde, time.min, timezone.utc))
        if hasta:
            q = q.where(Solicitud.creada_en <= datetime.combine(hasta, time.max, timezone.utc))
        return [{"flujo": f, "estado": e, "total": n} for f, e, n in s.execute(q)]


# --------------------------------------------------------------- IA y mantenimiento
class Consulta(BaseModel):
    texto: str = Field(max_length=500)


@router.post("/ia/sugerir")
def sugerir(d: Consulta, uid: int = Depends(actor_id)):
    """Sugerencia orientativa para el formulario web. No crea ni modifica nada."""
    try:
        sug = cascada.sugerir_texto(d.texto)
    except IANoDisponible as e:
        raise HTTPException(503, "IA no disponible") from e
    return {"categoria": sug.categoria, "confianza": sug.confianza, "origen": sug.origen, "flujos": sug.flujos}


@router.post("/mantenimiento/purgar-mensajes")
def purgar(uid: int = Depends(actor_id)):
    with sesion() as s:
        if _actor(s, uid).rol != "administrador":
            raise HTTPException(403, "Solo el administrador")
        return {"borrados": purgar_vencidos(s)}

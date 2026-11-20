"""API interna mínima (protegida con SERVICE_API_KEY en la cabecera X-Service-Key).

Supuesto: la web y la autenticación de usuarios de la especificación principal se conectan aquí.
"""
import hmac
from datetime import date, time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from .. import solicitudes, telefono
from ..config import config
from ..db import sesion
from ..ia import cascada
from ..ia.modelo import IANoDisponible
from ..models import CasoCoordinacion, Usuario
from ..whatsapp.mensajeria import purgar_vencidos


def clave_servicio(x_service_key: str = Header("")):
    esperada = config().service_api_key
    if not esperada or not hmac.compare_digest(x_service_key, esperada):
        raise HTTPException(401, "Clave de servicio inválida")


router = APIRouter(prefix="/api", dependencies=[Depends(clave_servicio)])


class NuevaSolicitud(BaseModel):
    telefono: str
    flujo: str
    descripcion: str = ""
    direccion: str | None = None


class Programacion(BaseModel):
    fecha: date
    hora: time
    encargado_id: int | None = None


class Consulta(BaseModel):
    texto: str


def _sol(sol):
    return {"codigo": sol.codigo, "flujo": sol.flujo, "estado": sol.estado,
            "fecha_programada": sol.fecha_programada, "hora_programada": sol.hora_programada}


@router.post("/solicitudes", status_code=201)
def crear_solicitud(d: NuevaSolicitud):
    with sesion() as s:
        u = s.scalar(select(Usuario).where(Usuario.telefono == telefono.normalizar(d.telefono)))
        if not u:
            raise HTTPException(404, "Usuario no registrado")
        try:
            return _sol(solicitudes.crear(s, u, d.flujo, d.descripcion, d.direccion))
        except solicitudes.ErrorSolicitud as e:
            raise HTTPException(400, str(e)) from e


@router.post("/solicitudes/{codigo}/programar")
def programar(codigo: str, d: Programacion):
    with sesion() as s:
        try:
            return _sol(solicitudes.programar(s, codigo.upper(), d.fecha, d.hora, d.encargado_id))
        except solicitudes.ErrorSolicitud as e:
            raise HTTPException(404, str(e)) from e


@router.post("/ia/sugerir")
def sugerir(d: Consulta):
    """Sugerencia para la web (solo texto). No crea nada."""
    try:
        sug = cascada.sugerir_texto(d.texto)
    except IANoDisponible as e:
        raise HTTPException(503, "IA no disponible") from e
    return {"categoria": sug.categoria, "confianza": sug.confianza, "origen": sug.origen, "flujos": sug.flujos}


@router.get("/bandeja")
def bandeja(flujo: str | None = None, estado: str = "abierto"):
    with sesion() as s:
        q = select(CasoCoordinacion).where(CasoCoordinacion.estado == estado)
        if flujo:
            q = q.where(CasoCoordinacion.flujo.in_([flujo, "general"]))
        casos = s.scalars(q.order_by(CasoCoordinacion.id.desc()).limit(200)).all()
        return [{"id": c.id, "flujo": c.flujo, "motivo": c.motivo, "resumen": c.resumen,
                 "usuario": c.usuario.nombre if c.usuario else None, "creado_en": c.creado_en} for c in casos]


@router.post("/mantenimiento/purgar-mensajes")
def purgar():
    with sesion() as s:
        return {"borrados": purgar_vencidos(s)}

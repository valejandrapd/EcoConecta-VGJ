"""Reglas de negocio de solicitudes. Las crean y programan PERSONAS (web/coordinación), nunca la IA."""
from datetime import date, time

from sqlalchemy import select

from .models import PREFIJO_FLUJO, SEQ_ORG, SEQ_REC, Solicitud, Usuario
from .notificaciones import obtener_notificador


class ErrorSolicitud(ValueError):
    pass


def _nuevo_codigo(s, flujo: str) -> str:
    seq = SEQ_ORG if flujo == "organico" else SEQ_REC
    return f"{PREFIJO_FLUJO[flujo]}-{s.scalar(seq.next_value()):04d}"


def crear(s, usuario: Usuario, flujo: str, descripcion: str = "", direccion: str | None = None) -> Solicitud:
    if flujo not in PREFIJO_FLUJO:
        raise ErrorSolicitud("flujo debe ser 'organico' o 'reciclable'")
    sol = Solicitud(codigo=_nuevo_codigo(s, flujo), usuario=usuario, flujo=flujo, estado="recibida",
                    descripcion=descripcion or None, direccion=direccion or usuario.direccion)
    s.add(sol)
    s.flush()
    n = obtener_notificador()
    n.solicitud_recibida(s, sol)
    n.nueva_solicitud(s, sol)
    return sol


def programar(s, codigo: str, fecha: date, hora: time, encargado_id: int | None) -> Solicitud:
    sol = s.scalar(select(Solicitud).where(Solicitud.codigo == codigo))
    if not sol:
        raise ErrorSolicitud("No existe esa solicitud")
    if encargado_id is not None and not s.get(Usuario, encargado_id):
        raise ErrorSolicitud("El encargado no existe")
    sol.estado, sol.fecha_programada, sol.hora_programada, sol.encargado_id = "programada", fecha, hora, encargado_id
    s.flush()
    s.refresh(sol)
    obtener_notificador().solicitud_programada(s, sol)
    return sol

"""Notificaciones del sistema por WhatsApp, usando el MISMO cliente y la misma mensajería del bot.

NOTIFICADOR=whatsapp -> WhatsAppNotificador (Graph API de Meta)
NOTIFICADOR=log      -> LogNotificador (sin credenciales: solo escribe en el log)

Dentro de la ventana de 24 h se envía texto; fuera de ella, la plantilla aprobada.
"""
import logging

from sqlalchemy import select

from .config import config
from .models import COORDINADOR_DE_FLUJO, Solicitud, Usuario
from .whatsapp import mensajeria
from .whatsapp.cliente import ClienteLog, ClienteWhatsApp, obtener_cliente
from .whatsapp.textos import NOMBRE_FLUJO

log = logging.getLogger("ecoconecta.notificaciones")


def _wa_id(tel: str) -> str:
    return (tel or "").lstrip("+")


class Notificador:
    def __init__(self, cliente=None):
        self.cliente = cliente or obtener_cliente()

    def solicitud_recibida(self, s, sol: Solicitud):
        cfg = config()
        mensajeria.enviar(
            s, _wa_id(sol.usuario.telefono), cliente=self.cliente, usuario_id=sol.usuario_id, intencion="solicitud_recibida",
            texto=f"Recibimos tu solicitud *{sol.codigo}* ({NOMBRE_FLUJO[sol.flujo]}). "
                  "Te avisaremos cuando esté programada. Consulta el estado escribiendo el código.",
            plantilla=cfg.plantilla_solicitud_recibida, parametros=[sol.codigo])

    def nueva_solicitud(self, s, sol: Solicitud):
        cfg = config()
        coordinadores = s.scalars(select(Usuario).where(
            Usuario.rol == COORDINADOR_DE_FLUJO[sol.flujo], Usuario.activo.is_(True))).all()
        for c in coordinadores:  # al coordinador no se le envían datos personales del ciudadano
            mensajeria.enviar(
                s, _wa_id(c.telefono), cliente=self.cliente, usuario_id=c.id, intencion="nueva_solicitud",
                texto=f"Nueva solicitud *{sol.codigo}* ({NOMBRE_FLUJO[sol.flujo]}). Revísala en la bandeja.",
                plantilla=cfg.plantilla_nueva_solicitud, parametros=[sol.codigo])

    def solicitud_programada(self, s, sol: Solicitud):
        cfg = config()
        fecha = f"{sol.fecha_programada:%d/%m/%Y}" if sol.fecha_programada else ""
        hora = f"{sol.hora_programada:%H:%M}" if sol.hora_programada else ""
        encargado = sol.reciclador.nombre if sol.reciclador else ""
        mensajeria.enviar(
            s, _wa_id(sol.usuario.telefono), cliente=self.cliente, usuario_id=sol.usuario_id, intencion="solicitud_programada",
            texto=f"Tu solicitud *{sol.codigo}* quedó programada para el {fecha} a las {hora}"
                  + (f" con {encargado}." if encargado else "."),
            plantilla=cfg.plantilla_solicitud_programada, parametros=[sol.codigo, fecha, hora, encargado or "-"])


class WhatsAppNotificador(Notificador):
    def __init__(self):
        super().__init__(ClienteWhatsApp())


class LogNotificador(Notificador):
    def __init__(self):
        super().__init__(ClienteLog())


def obtener_notificador() -> Notificador:
    from .whatsapp import cliente as _c
    if _c._cliente_forzado is not None:  # pruebas
        return Notificador(_c._cliente_forzado)
    if config().whatsapp_activo:
        return WhatsAppNotificador()
    if config().notificador == "whatsapp":
        log.warning("NOTIFICADOR=whatsapp pero faltan credenciales: se usa LogNotificador")
    return LogNotificador()

"""Envío de mensajes con la regla de la ventana de 24 h y registro mínimo en `mensajes_whatsapp`.

Dentro de la ventana (24 h desde el último mensaje del usuario) se envía texto libre.
Fuera de ella solo se pueden enviar plantillas aprobadas por Meta.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from ..config import config
from ..models import ConversacionWhatsapp, MensajeWhatsapp
from .cliente import ErrorWhatsApp, obtener_cliente

log = logging.getLogger("ecoconecta.whatsapp")
VENTANA = timedelta(hours=24)


def _ahora():
    return datetime.now(timezone.utc)


def _retener_hasta():
    return _ahora() + timedelta(days=config().retencion_mensajes_dias)


def registrar_entrante(s, wa_message_id: str, wa_id: str, tipo: str, usuario_id=None) -> bool:
    """Guarda el id del mensaje de Meta. Devuelve False si ya existía (reintento duplicado)."""
    res = s.execute(
        insert(MensajeWhatsapp)
        .values(wa_message_id=wa_message_id, wa_id=wa_id, usuario_id=usuario_id, direccion="entrante",
                tipo=tipo, creado_en=_ahora(), retener_hasta=_retener_hasta())
        .on_conflict_do_nothing(constraint="uq_mensajes_wa_message_id")
        .returning(MensajeWhatsapp.id)
    ).first()
    if res is None:
        return False
    conv = s.get(ConversacionWhatsapp, wa_id) or ConversacionWhatsapp(wa_id=wa_id, fallos_seguidos=0)
    conv.ultimo_entrante_en = _ahora()
    s.add(conv)
    return True


def marcar_intencion(s, wa_message_id: str, intencion: str):
    msg = s.scalar(select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == wa_message_id))
    if msg:
        msg.intencion = intencion


def entrantes_hoy(s, wa_id: str) -> int:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(config().zona_horaria)
    inicio = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    return s.scalar(select(func.count()).select_from(MensajeWhatsapp).where(
        MensajeWhatsapp.wa_id == wa_id, MensajeWhatsapp.direccion == "entrante",
        MensajeWhatsapp.creado_en >= inicio)) or 0


def dentro_de_ventana(s, wa_id: str) -> bool:
    conv = s.get(ConversacionWhatsapp, wa_id)
    return bool(conv and conv.ultimo_entrante_en and _ahora() - conv.ultimo_entrante_en < VENTANA)


def enviar(s, wa_id: str, *, texto: str | None = None, plantilla: str | None = None,
           parametros: list[str] | None = None, intencion: str | None = None, usuario_id=None,
           cliente=None) -> bool:
    """Envía texto si la ventana está abierta; si no, la plantilla (si se indicó).

    Devuelve True si se envió. Nunca lanza por fallos de la Graph API: los registra como 'fallido'.
    """
    cliente = cliente or obtener_cliente()
    usar_texto = texto is not None and dentro_de_ventana(s, wa_id)
    if not usar_texto and not plantilla:
        log.info("Fuera de la ventana de 24 h y sin plantilla: no se envía (%s)", intencion)
        return False
    estado = "log" if cliente.__class__.__name__ == "ClienteLog" else "enviado"
    try:
        if usar_texto:
            cliente.enviar_texto(wa_id, texto)
        else:
            cliente.enviar_plantilla(wa_id, plantilla, parametros or [])
    except ErrorWhatsApp as e:
        log.warning("No se pudo enviar el mensaje (%s): %s", intencion, e)
        estado = "fallido"
    s.add(MensajeWhatsapp(wa_id=wa_id, usuario_id=usuario_id, direccion="saliente",
                          tipo="texto" if usar_texto else "plantilla",
                          plantilla=None if usar_texto else plantilla, intencion=intencion,
                          estado_envio=estado, creado_en=_ahora(), retener_hasta=_retener_hasta()))
    return estado != "fallido"


def purgar_vencidos(s) -> int:
    """Borra los registros cuya retención venció (RETENCION_MENSAJES_DIAS)."""
    from sqlalchemy import delete
    return s.execute(delete(MensajeWhatsapp).where(MensajeWhatsapp.retener_hasta < _ahora())).rowcount

"""Avisos al usuario por WhatsApp cuando cambia su solicitud (confirmación, programación, recolección, cancelación).

Lo dispara quien cambie el estado: el backend provisional (api.py) o el backend real llamando a
POST /api/v1/notificar con {"codigo": "RES-..."}.
"""
import backend
import whapi


def _programacion(s):
    p = s.get("programacion") or {}
    if p:
        return f"{p['dia']} a las {p['hora']}, con {p['recolector']}"
    return ""


def mensaje_para(s):
    """Texto del aviso según el estado actual de la solicitud (o None si no corresponde avisar)."""
    c, flujo = s["codigo"], s["flujo"]
    est = s["estado"]
    if est == "recibida":
        return (f"✅ Recibimos tu solicitud *{c}*. Va al coordinador de *{flujo}*. "
                "Te avisaré por aquí cuando esté programada.")
    if est == "asignada":
        return f"👤 Tu solicitud *{c}* fue asignada a *{s['recolector']}*. Pronto te confirmaremos día y hora."
    if est == "programada":
        return f"📅 Tu solicitud *{c}* quedó *programada*: {_programacion(s)}."
    if est == "recolectada":
        return f"🎉 Registramos la recolección de *{c}*. ¡Ganaste *{s['puntos']} puntos*! Gracias por participar."
    if est == "cancelada":
        return f"Tu solicitud *{c}* fue *cancelada*. Si quieres, puedes crear una nueva desde el menú."
    return None


def notificar(codigo, enviar=None):
    """Envía el aviso del estado actual. Devuelve el texto enviado, o None si el canal no es WhatsApp."""
    enviar = enviar or whapi.enviar_texto
    s = backend.consultar(codigo)
    if s.get("canal") != "whatsapp":
        return None
    texto = mensaje_para(s)
    if texto:
        enviar(s["contacto"], texto)
    return texto

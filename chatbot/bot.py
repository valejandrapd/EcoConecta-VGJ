"""Adaptador de WhatsApp (Whapi.Cloud): traduce los mensajes del webhook a `conversacion.atender` y envía las respuestas."""
import logging
import threading

import conversacion

log = logging.getLogger("ecoconecta")
_candados = {}
_guarda = threading.Lock()


def _candado(contacto):
    with _guarda:
        return _candados.setdefault(contacto, threading.Lock())


def _telefono(chat_id: str) -> str:
    return chat_id.split("@")[0]


def procesar(msg: dict, enviar, descargar_imagen, clasificar_foto, segmentar_foto=None, transcribir=None, descargar_audio=None):
    """Procesa UN mensaje del webhook. Las dependencias externas se inyectan:
    enviar(destino, texto) · descargar_imagen(bloque_imagen) -> (bytes, mime) · clasificar_foto(bytes, mime) -> (cat, objeto)
    segmentar_foto(bytes, mime) -> [(cat, objeto), ...] (varios residuos en una foto)
    descargar_audio(bloque) -> (bytes, mime) · transcribir(bytes, mime) -> texto (None = audios no habilitados)
    """
    chat_id = msg.get("chat_id", "")
    if msg.get("from_me") or chat_id.endswith("@g.us"):
        return  # ignora mis propios mensajes y los grupos
    tel, tipo = _telefono(chat_id), msg.get("type")
    with _candado(tel):  # un mensaje a la vez por persona, para no mezclar pasos de la conversación
        try:
            if tipo == "text":
                resp = conversacion.atender(tel, texto=(msg.get("text") or {}).get("body", ""))
            elif tipo == "image":
                imagen = msg.get("image") or {}
                resp = conversacion.atender(tel, foto=lambda: descargar_imagen(imagen), clasificar_foto=clasificar_foto,
                                            segmentar_foto=segmentar_foto)
            elif tipo in ("voice", "audio", "ptt"):
                resp = _audio(msg, tel, transcribir, descargar_audio, clasificar_foto, segmentar_foto)
            else:
                resp = [conversacion.SOLO_TEXTO_FOTO, conversacion.MENU]
        except Exception:  # noqa: BLE001
            log.exception("Error atendiendo el mensaje %s", msg.get("id"))
            resp = ["Ups, algo falló de mi lado. Intenta de nuevo en un momento 🙏"]
        for texto in resp:
            enviar(tel, texto)


MAX_AUDIO_SEG = 180
SIN_AUDIO = "Aún no puedo escuchar audios 🎙️. Escríbeme lo que quieres entregar o envíame una foto 📷."
AUDIO_NO_ENTENDIDO = "No logré entender el audio 🙏. ¿Puedes repetirlo más cerca del micrófono o escribirlo?"


def _audio(msg, tel, transcribir, descargar_audio, clasificar_foto, segmentar_foto):
    """Audio -> texto -> mismo flujo que si la persona lo hubiera escrito (y se le muestra lo que se entendió)."""
    if transcribir is None or descargar_audio is None:
        return [SIN_AUDIO]
    bloque = msg.get("voice") or msg.get("audio") or msg.get("ptt") or {}
    if (bloque.get("seconds") or 0) > MAX_AUDIO_SEG:
        return ["Ese audio es muy largo. Envíame uno de menos de 3 minutos, por favor 🙏"]
    datos, mime = descargar_audio(bloque)
    texto = (transcribir(datos, mime) or "").strip()
    if not texto:
        return [AUDIO_NO_ENTENDIDO]
    resp = conversacion.atender(tel, texto=texto, clasificar_foto=clasificar_foto, segmentar_foto=segmentar_foto, origen="audio")
    return [f"🎙️ Entendí: «{texto}»"] + resp

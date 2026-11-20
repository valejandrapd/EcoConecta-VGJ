"""Adaptador de WhatsApp: traduce mensajes de Whapi a llamadas a `core` y arma las respuestas.

La lógica de clasificación vive en `core.py` (la misma que usa la API REST para apps y webs).

Flujo:
  1. Llega un texto con el residuo  -> se crea una solicitud con ID único (RES-AAAAMMDD-NNNN).
  2. Si el texto alcanza para decidir -> responde ORGÁNICO o RECICLABLE.
  3. Si no se sabe qué residuo es    -> pide una FOTO y lo identifica por cámara.
"""
import logging

import core
import db
from clasificador import ORGANICO, RECICLABLE

log = logging.getLogger("ecoconecta")

AYUDA = (
    "♻️ *EcoConecta*\n"
    "Escríbeme qué residuo tienes (por ejemplo: _cáscara de banano_ o _botella de plástico_) "
    "y te digo si es *orgánico* o *reciclable*.\n"
    "Si no logro identificarlo, te pediré una *foto*.\n"
    "Para consultar una solicitud: *estado RES-20261120-0001*"
)

CONSEJOS = {
    ORGANICO: "🟢 *ORGÁNICO*. Va en la bolsa/caneca de residuos orgánicos (compostable).",
    RECICLABLE: "🔵 *RECICLABLE*. Va en la bolsa/caneca de reciclaje. Entrégalo limpio y seco.",
    "OTRO": "⚫ *NO APROVECHABLE*. No es ni orgánico ni reciclable: va en la caneca de residuos ordinarios.",
}


def _telefono(chat_id: str) -> str:
    return chat_id.split("@")[0]


def _respuesta_final(codigo, categoria, metodo, objeto=""):
    que = f" ({objeto})" if objeto else ""
    via = "por tu foto 📷" if metodo == "foto" else "por tu mensaje"
    return f"Solicitud *{codigo}*\nIdentificado {via}{que}:\n{CONSEJOS[categoria]}"


def procesar(msg: dict, enviar, descargar_imagen, clasificar_foto):
    """Procesa UN mensaje del webhook. Las dependencias externas se inyectan:
    enviar(destino, texto) · descargar_imagen(bloque_imagen) -> (bytes, mime) · clasificar_foto(bytes, mime) -> (cat, objeto)
    """
    chat_id = msg.get("chat_id", "")
    if msg.get("from_me") or chat_id.endswith("@g.us"):
        return  # ignora mis propios mensajes y los grupos
    tel = _telefono(chat_id)
    tipo = msg.get("type")

    if tipo == "text":
        texto = (msg.get("text") or {}).get("body", "").strip()
        return _procesar_texto(tel, texto, enviar)
    if tipo == "image":
        return _procesar_foto(tel, msg.get("image") or {}, enviar, descargar_imagen, clasificar_foto)
    enviar(tel, "Por ahora solo entiendo *texto* y *fotos* de residuos 🙂\n\n" + AYUDA)


def _procesar_texto(tel, texto, enviar):
    bajo = texto.lower()
    if not texto or bajo in {"hola", "ayuda", "menu", "menú", "hi", "buenas"}:
        return enviar(tel, AYUDA)

    if bajo.startswith(("estado", "consultar")):
        codigo = texto.split()[-1].upper() if len(texto.split()) > 1 else ""
        fila = db.obtener(codigo) if codigo else None
        if not fila:
            return enviar(tel, "No encontré esa solicitud. Revisa el código (ej.: RES-20261120-0001).")
        res = fila["categoria"] or "pendiente (esperando foto)"
        return enviar(tel, f"Solicitud *{fila['codigo']}*: {res}.")

    r = core.registrar_texto(tel, texto, canal="whatsapp")
    if r["categoria"]:
        return enviar(tel, _respuesta_final(r["codigo"], r["categoria"], "texto"))

    enviar(tel, f"Solicitud *{r['codigo']}* registrada.\n"
                "No logré identificar ese residuo solo con el texto. "
                "📷 *Envíame una foto del residuo* y lo identifico por cámara.")


def _procesar_foto(tel, imagen, enviar, descargar_imagen, clasificar_foto):
    pendiente = db.pendiente_de_foto(tel)
    codigo = pendiente["codigo"] if pendiente else db.crear(tel, "(solo foto)", "whatsapp")
    try:
        datos, mime = descargar_imagen(imagen)
        r = core.adjuntar_foto(tel, datos, mime, clasificar_foto, canal="whatsapp", codigo=codigo)
    except Exception:  # noqa: BLE001 - el usuario debe recibir una respuesta amable
        log.exception("Fallo al procesar la foto de la solicitud %s", codigo)
        return enviar(tel, f"Solicitud *{codigo}*: no pude procesar la foto. Intenta enviarla de nuevo, por favor.")

    if r["foto_ilegible"]:
        return enviar(tel, f"Solicitud *{codigo}*: no distingo el residuo en la foto. "
                           "Toma otra foto más cerca y con buena luz 📷")
    enviar(tel, _respuesta_final(codigo, r["categoria"], "foto", r["objeto"]))

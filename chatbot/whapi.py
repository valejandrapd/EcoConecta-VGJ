"""Cliente mínimo de Whapi.Cloud (solo librería estándar): enviar texto y descargar imágenes y audios."""
import json
import os
import urllib.request

BASE = "https://gate.whapi.cloud"


def _pedir(url, datos=None, con_token=True):
    # User-Agent propio: Cloudflare (Whapi) bloquea el de urllib por defecto.
    cab = {"Accept": "application/json", "User-Agent": "ecoconecta-chatbot/1.0"}
    if con_token:
        cab["Authorization"] = "Bearer " + os.environ["WHAPI_TOKEN"]
    cuerpo = None
    if datos is not None:
        cuerpo = json.dumps(datos).encode()
        cab["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=cuerpo, headers=cab)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def enviar_texto(destino: str, texto: str):
    return json.loads(_pedir(f"{BASE}/messages/text", {"to": destino, "body": texto}) or b"{}")


def descargar_media(bloque: dict, mime_defecto="image/jpeg"):
    """Recibe el bloque `image`, `voice` o `audio` del webhook y devuelve (bytes, mime)."""
    mime = bloque.get("mime_type", mime_defecto).split(";")[0]
    if bloque.get("link"):  # con "Auto Download" activo en el panel de Whapi
        return _pedir(bloque["link"], con_token=False), mime
    return _pedir(f"{BASE}/media/{bloque['id']}"), mime


def descargar_imagen(imagen: dict):
    return descargar_media(imagen)


def descargar_audio(audio: dict):
    return descargar_media(audio, "audio/ogg")

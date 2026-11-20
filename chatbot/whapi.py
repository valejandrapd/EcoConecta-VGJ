"""Cliente mínimo de Whapi.Cloud: enviar texto y descargar imágenes."""
import os

import requests

BASE = "https://gate.whapi.cloud"


def _headers():
    return {
        "Authorization": "Bearer " + os.environ["WHAPI_TOKEN"],
        "Accept": "application/json",
        "User-Agent": "ecoconecta-chatbot/1.0",
    }


def enviar_texto(destino: str, texto: str):
    r = requests.post(f"{BASE}/messages/text", json={"to": destino, "body": texto},
                      headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def descargar_imagen(imagen: dict):
    """Recibe el bloque `image` del webhook y devuelve (bytes, mime)."""
    mime = imagen.get("mime_type", "image/jpeg").split(";")[0]
    if imagen.get("link"):  # con "Auto Download" activo en el panel de Whapi
        r = requests.get(imagen["link"], timeout=30)
    else:
        r = requests.get(f"{BASE}/media/{imagen['id']}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.content, mime

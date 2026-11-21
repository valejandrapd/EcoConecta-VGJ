"""Puerta de entrada del chatbot al backend de solicitudes.

  · Sin BACKEND_URL  -> usa el backend PROVISIONAL incluido (core.py + base de datos propia).
  · Con BACKEND_URL  -> llama al backend REAL del equipo, que debe cumplir docs/CONTRATO_BACKEND.md
                        (la misma API /api/v1 que expone este proyecto). BACKEND_API_KEY es opcional.
Así, cambiar de backend es solo configuración: el bot no se toca.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import core


def _remoto():
    return os.environ.get("BACKEND_URL", "").rstrip("/")


def _http(metodo, ruta, datos=None, consulta=None):
    url = _remoto() + ruta + ("?" + urllib.parse.urlencode(consulta) if consulta else "")
    cab = {"Accept": "application/json", "User-Agent": "ecoconecta-chatbot/1.0"}
    if os.environ.get("BACKEND_API_KEY"):
        cab["X-API-Key"] = os.environ["BACKEND_API_KEY"]
    cuerpo = None
    if datos is not None:
        cuerpo = json.dumps(datos).encode()
        cab["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, cuerpo, cab, method=metodo), timeout=30) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            mensaje = json.loads(e.read()).get("error", "")
        except Exception:  # noqa: BLE001
            mensaje = ""
        if e.code == 404:
            raise core.SolicitudNoEncontrada(ruta) from None
        if e.code in (400, 409, 422):
            raise core.DatosInvalidos(mensaje or "Datos no válidos") from None
        raise


def crear_solicitud(datos):
    return _http("POST", "/solicitudes", datos) if _remoto() else core.crear_solicitud(datos)


def consultar(codigo, contacto=None):
    if _remoto():
        return _http("GET", "/solicitudes/" + urllib.parse.quote(str(codigo)), consulta={"contacto": contacto} if contacto else None)
    return core.consultar(codigo, contacto)


def listar(contacto, limite=3):
    if _remoto():
        return _http("GET", "/solicitudes", consulta={"contacto": contacto, "limite": limite})
    return core.listar(contacto=contacto, limite=limite)


def puntos(contacto):
    if _remoto():
        return int(_http("GET", "/puntos/" + urllib.parse.quote(str(contacto)))["puntos"])
    return core.puntos(contacto)

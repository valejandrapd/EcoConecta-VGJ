"""Único cliente de WhatsApp Business Cloud API (Graph API de Meta).

Lo usan el bot y las notificaciones del sistema. Con NOTIFICADOR=log (o sin credenciales) se usa
`ClienteLog`, que solo escribe en el log: sirve para desarrollo y demos sin número de Meta.
"""
import json
import logging
import urllib.error
import urllib.request

from ..config import config

log = logging.getLogger("ecoconecta.whatsapp")


class ErrorWhatsApp(RuntimeError):
    pass


def _ocultar(wa_id: str) -> str:
    return f"***{wa_id[-4:]}" if wa_id else "?"


class ClienteWhatsApp:
    """Cliente HTTP mínimo con la librería estándar (urllib): no añade dependencias."""

    def __init__(self, cfg=None):
        self.cfg = cfg or config()
        self.base = f"https://graph.facebook.com/{self.cfg.graph_version}"

    def _pedir(self, url: str, cuerpo: dict | None = None) -> bytes:
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(url, data=datos, method="POST" if datos else "GET",
                                     headers={"Authorization": f"Bearer {self.cfg.wa_token}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.graph_timeout_s) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ErrorWhatsApp(f"Graph API: {type(e).__name__}") from e

    def _post_mensaje(self, cuerpo: dict) -> str:
        url = f"{self.base}/{self.cfg.wa_phone_number_id}/messages"
        resp = json.loads(self._pedir(url, {"messaging_product": "whatsapp", **cuerpo}) or b"{}")
        return (resp.get("messages") or [{}])[0].get("id", "")

    def enviar_texto(self, wa_id: str, texto: str) -> str:
        return self._post_mensaje({"to": wa_id, "type": "text", "text": {"body": texto[:4096]}})

    def enviar_plantilla(self, wa_id: str, nombre: str, parametros: list[str]) -> str:
        plantilla = {"name": nombre, "language": {"code": self.cfg.plantilla_idioma}}
        if parametros:
            plantilla["components"] = [{"type": "body", "parameters": [
                {"type": "text", "text": str(p)} for p in parametros]}]
        return self._post_mensaje({"to": wa_id, "type": "template", "template": plantilla})

    def descargar_media(self, media_id: str) -> bytes:
        try:
            url = json.loads(self._pedir(f"{self.base}/{media_id}"))["url"]
        except (KeyError, ValueError) as e:
            raise ErrorWhatsApp("Descarga de media: respuesta inesperada") from e
        return self._pedir(url)


class ClienteLog:
    """Alternativa sin credenciales: registra en el log lo que se habría enviado."""

    def __init__(self):
        self.enviados = []  # últimos envíos (útil en demos); se limita a 100

    def enviar_texto(self, wa_id, texto):
        log.info("[log] texto a %s: %s", _ocultar(wa_id), texto.replace("\n", " | ")[:300])
        self.enviados = (self.enviados + [("texto", wa_id, texto)])[-100:]
        return "log"

    def enviar_plantilla(self, wa_id, nombre, parametros):
        log.info("[log] plantilla %s a %s: %s", nombre, _ocultar(wa_id), parametros)
        self.enviados = (self.enviados + [("plantilla", wa_id, nombre, list(parametros))])[-100:]
        return "log"

    def descargar_media(self, media_id):
        raise ErrorWhatsApp("Sin credenciales de WhatsApp no se pueden descargar fotos")


_cliente_forzado = None


def usar_cliente(cliente):
    """Permite inyectar un cliente (pruebas)."""
    global _cliente_forzado
    _cliente_forzado = cliente


def obtener_cliente():
    if _cliente_forzado is not None:
        return _cliente_forzado
    return ClienteWhatsApp() if config().whatsapp_activo else ClienteLog()

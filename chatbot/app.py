"""Servidor de EcoConecta: webhook de WhatsApp (/webhook) + API REST (/api/v1).

Local sin Docker:   pip install -r requirements.txt && python app.py      (http://localhost:5000)
Con Docker:         docker compose up --build                              (ver README)
Para recibir WhatsApp en tu PC:  ngrok http 5000  y poner https://TU-URL/webhook en Whapi (evento messages · post).
"""
import logging
import os
import threading
from collections import OrderedDict


def cargar_env(ruta=".env"):
    """Lee .env sin librerías extra (no pisa variables ya definidas)."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


cargar_env()  # antes de importar el resto: db.py lee DATABASE_URL

from flask import Flask, jsonify, request  # noqa: E402

import api  # noqa: E402
import bot  # noqa: E402
import db  # noqa: E402
import transcripcion  # noqa: E402
import vision  # noqa: E402
import whapi  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = Flask(__name__)
app.register_blueprint(api.bp)
app.config["MAX_CONTENT_LENGTH"] = api.max_foto_bytes() + 1024 * 1024
db.iniciar()

_vistos = OrderedDict()  # ids de mensajes ya atendidos (Whapi puede reintentar el webhook)
_guarda = threading.Lock()


def _nuevo(id_msg):
    with _guarda:
        if id_msg in _vistos:
            return False
        _vistos[id_msg] = True
        while len(_vistos) > 2000:
            _vistos.popitem(last=False)
        return True


def _atender(msg):
    try:
        bot.procesar(msg, whapi.enviar_texto, whapi.descargar_imagen, vision.clasificar_foto, vision.segmentar_foto,
                     transcripcion.transcribir if transcripcion.configurada() else None, whapi.descargar_audio)
    except Exception:  # noqa: BLE001
        logging.exception("Error atendiendo el mensaje %s", msg.get("id"))


@app.errorhandler(413)
def _demasiado_grande(_):
    return jsonify(error="La foto es demasiado grande."), 413


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/webhook")
def webhook():
    datos = request.get_json(silent=True) or {}
    for msg in datos.get("messages", []):
        logging.info("webhook: tipo=%s from_me=%s chat=%s", msg.get("type"), msg.get("from_me"), str(msg.get("chat_id", ""))[-18:])
        if msg.get("id") and not _nuevo(msg["id"]):
            continue
        # se responde 200 de inmediato; la clasificación (puede tardar) va en segundo plano
        threading.Thread(target=_atender, args=(msg,), daemon=True).start()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

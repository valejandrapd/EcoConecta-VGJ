"""Servidor de EcoConecta: webhook de WhatsApp (/webhook) + API REST para apps y webs (/api/v1).

Uso local:
    python app.py            -> escucha en http://localhost:5000
    ngrok http 5000          -> da una URL pública; ponla en el panel de Whapi (Webhooks) como
                                https://TU-URL.ngrok-free.app/webhook  (evento: messages · post)
"""
import logging
import os
import threading

from flask import Flask, jsonify, request

import api
import bot
import db
import vision
import whapi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = Flask(__name__)
app.register_blueprint(api.bp)
db.iniciar()


def cargar_env(ruta=".env"):
    """Lee .env sin librerías extra (no pisa variables ya definidas)."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


cargar_env()
app.config["MAX_CONTENT_LENGTH"] = api.max_foto_bytes() + 1024 * 1024


def _atender(msg):
    try:
        bot.procesar(msg, whapi.enviar_texto, whapi.descargar_imagen, vision.clasificar_foto)
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
        # se responde 200 de inmediato; la clasificación (puede tardar) va en segundo plano
        threading.Thread(target=_atender, args=(msg,), daemon=True).start()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

"""Webhook de WhatsApp Business Cloud API: un solo endpoint, /webhook.

GET  /webhook  verificación de Meta (hub.mode, hub.verify_token, hub.challenge)
POST /webhook  mensajes entrantes: firma X-Hub-Signature-256, 200 inmediato, proceso en segundo plano
"""
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from ..config import config
from ..db import sesion
from . import bot
from .firma import firma_valida
from .mensajeria import registrar_entrante

log = logging.getLogger("ecoconecta.webhook")
router = APIRouter()

TIPOS = {"text": "texto", "image": "imagen", "audio": "audio"}


@router.get("/webhook", response_class=PlainTextResponse)
def verificar(hub_mode: str = Query("", alias="hub.mode"),
              hub_verify_token: str = Query("", alias="hub.verify_token"),
              hub_challenge: str = Query("", alias="hub.challenge")):
    esperado = config().wa_verify_token
    if hub_mode == "subscribe" and esperado and hmac.compare_digest(hub_verify_token, esperado):
        return hub_challenge
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/webhook")
async def recibir(request: Request, tareas: BackgroundTasks):
    cuerpo = await request.body()
    if not firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256"), config().wa_app_secret):
        log.warning("Webhook rechazado: firma inválida")
        raise HTTPException(status_code=403, detail="Firma inválida")
    try:
        datos = json.loads(cuerpo or b"{}")
    except json.JSONDecodeError:
        return {"ok": True}  # 200 para que Meta no reintente basura

    nuevos = duplicados = 0
    for entrada in datos.get("entry", []):
        for cambio in entrada.get("changes", []):
            valor = cambio.get("value") or {}
            for msg in valor.get("messages", []):  # los "statuses" (entregado/leído) se ignoran
                if not msg.get("id") or not msg.get("from"):
                    continue
                with sesion() as s:
                    es_nuevo = registrar_entrante(s, msg["id"], msg["from"], TIPOS.get(msg.get("type"), "otro"))
                if es_nuevo:
                    nuevos += 1
                    tareas.add_task(bot.procesar, msg)
                else:
                    duplicados += 1
    return {"ok": True, "nuevos": nuevos, "duplicados": duplicados}

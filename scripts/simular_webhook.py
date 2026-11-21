"""Envía al webhook local un mensaje firmado como lo haría Meta (para probar sin número real).

Uso:
    WHATSAPP_APP_SECRET=... python scripts/simular_webhook.py 573000000001 "hola"
    WHATSAPP_APP_SECRET=... python scripts/simular_webhook.py 573000000001 "ORG-0042" --url http://localhost:8000/webhook
Con NOTIFICADOR=log, la respuesta del bot aparece en los logs del backend.
"""
import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.request

p = argparse.ArgumentParser()
p.add_argument("wa_id")
p.add_argument("texto")
p.add_argument("--url", default="http://localhost:8000/webhook")
a = p.parse_args()

secreto = os.environ["WHATSAPP_APP_SECRET"]
carga = {"object": "whatsapp_business_account", "entry": [{"id": "SIM", "changes": [{"field": "messages", "value": {
    "messaging_product": "whatsapp", "metadata": {"phone_number_id": "SIM"},
    "messages": [{"from": a.wa_id, "id": f"wamid.sim.{time.time_ns()}", "timestamp": str(int(time.time())),
                  "type": "text", "text": {"body": a.texto}}]}}]}]}
cuerpo = json.dumps(carga).encode()
firma = "sha256=" + hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
req = urllib.request.Request(a.url, data=cuerpo, method="POST",
                             headers={"Content-Type": "application/json", "X-Hub-Signature-256": firma})
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.status, r.read().decode())

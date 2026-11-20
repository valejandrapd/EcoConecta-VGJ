"""Identificación del residuo por cámara (foto) usando la API de Claude."""
import base64
import json
import os
import re

import anthropic

MODELO = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

PROMPT = (
    "Mira la foto de un residuo y clasifícalo para separación en la fuente. "
    "Responde SOLO con un JSON: "
    '{"categoria": "ORGANICO" | "RECICLABLE" | "OTRO" | "NO_SE_VE", "objeto": "<nombre corto en español>"}. '
    "ORGANICO = restos de comida, cáscaras, hojas, restos vegetales. "
    "RECICLABLE = plástico, vidrio, metal, papel, cartón limpios. "
    "OTRO = residuos que no son ni orgánicos ni reciclables (higiénicos, mezclados, peligrosos). "
    "NO_SE_VE = la foto no muestra un residuo identificable."
)


def clasificar_foto(imagen: bytes, mime: str = "image/jpeg"):
    """Devuelve (categoria, objeto). categoria: ORGANICO | RECICLABLE | OTRO | NO_SE_VE."""
    cliente = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY del entorno
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": mime,
                    "data": base64.b64encode(imagen).decode("ascii")}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    texto = "".join(b.text for b in respuesta.content if b.type == "text")
    return interpretar(texto)


def interpretar(texto: str):
    """Extrae (categoria, objeto) de la respuesta del modelo, tolerando texto extra."""
    m = re.search(r"\{.*\}", texto, re.S)
    try:
        datos = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        datos = {}
    categoria = str(datos.get("categoria", "NO_SE_VE")).upper()
    if categoria not in {"ORGANICO", "RECICLABLE", "OTRO", "NO_SE_VE"}:
        categoria = "NO_SE_VE"
    return categoria, str(datos.get("objeto", "")).strip()

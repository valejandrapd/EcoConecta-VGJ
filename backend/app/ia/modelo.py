"""Pasos 2 y 3 de la cascada: modelo con texto y con visión.

Proveedores autorizados por el reto (sección 8), según IA_PROVEEDOR:
- claude: Claude API con el SDK oficial de Anthropic.
- azure_openai: Azure OpenAI (Azure AI Foundry) con el SDK oficial de OpenAI.

Privacidad: solo se envía la descripción del residuo o la foto ya limpia. Nunca nombre,
teléfono ni dirección. Tiempo máximo de espera configurable con IA_TIMEOUT_S.
"""
import base64
import json
import logging
import re

import anthropic

from ..config import config

log = logging.getLogger("ecoconecta.ia")


class IANoDisponible(RuntimeError):
    """Sin clave, tiempo agotado o error del proveedor: el bot responde con un mensaje de contingencia."""


INSTRUCCIONES = (
    "Eres el asistente de separación en la fuente de EcoConecta. Clasifica el residuo descrito "
    "o mostrado. Responde SOLO con un JSON en una línea: "
    '{"categoria": "ORGANICO" | "RECICLABLE" | "MEZCLA" | "NO_APROVECHABLE" | "DESCONOCIDO", '
    '"objeto": "<nombre corto en español>", "confianza": "alta" | "media" | "baja"}. '
    "ORGANICO = restos de comida, cáscaras, hojas, restos vegetales. "
    "RECICLABLE = plástico, vidrio, metal, papel o cartón limpios. "
    "MEZCLA = hay residuos orgánicos y reciclables juntos. "
    "NO_APROVECHABLE = ni orgánico ni reciclable (higiénicos, peligrosos, contaminados). "
    "DESCONOCIDO = no se entiende o no se ve un residuo."
)

CATEGORIAS = {"ORGANICO", "RECICLABLE", "MEZCLA", "NO_APROVECHABLE", "DESCONOCIDO"}


def _cliente():
    cfg = config()
    if not cfg.anthropic_api_key:
        raise IANoDisponible("Falta ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=cfg.anthropic_api_key, timeout=cfg.ia_timeout_s, max_retries=1)


def _llamar(modelo: str, contenido: list) -> dict:
    if config().ia_proveedor == "azure_openai":
        return _llamar_azure(contenido)
    return _llamar_claude(modelo, contenido)


def _llamar_azure(contenido: list) -> dict:
    """Mismo contrato con Azure OpenAI: traduce las partes (texto e imagen) al formato de chat."""
    cfg = config()
    if not (cfg.azure_openai_endpoint and cfg.azure_openai_api_key):
        raise IANoDisponible("Faltan AZURE_OPENAI_ENDPOINT o AZURE_OPENAI_API_KEY")
    import openai
    partes = []
    for p in contenido:
        if p["type"] == "text":
            partes.append({"type": "text", "text": p["text"]})
        elif p["type"] == "image":
            partes.append({"type": "image_url", "image_url": {
                "url": f"data:{p['source']['media_type']};base64,{p['source']['data']}", "detail": "low"}})
    try:
        cliente = openai.AzureOpenAI(azure_endpoint=cfg.azure_openai_endpoint, api_key=cfg.azure_openai_api_key,
                                     api_version=cfg.azure_openai_api_version, timeout=cfg.ia_timeout_s,
                                     max_retries=1)
        resp = cliente.chat.completions.create(
            model=cfg.azure_openai_deployment, max_tokens=200, temperature=0,
            messages=[{"role": "system", "content": INSTRUCCIONES}, {"role": "user", "content": partes}])
    except openai.APITimeoutError as e:
        raise IANoDisponible("Tiempo de espera agotado") from e
    except openai.APIError as e:
        log.warning("Fallo de Azure OpenAI: %s", type(e).__name__)
        raise IANoDisponible(str(type(e).__name__)) from e
    eleccion = resp.choices[0] if resp.choices else None
    if not eleccion or eleccion.finish_reason == "content_filter":
        return {"categoria": "DESCONOCIDO", "objeto": "", "confianza": "baja"}
    return interpretar(eleccion.message.content or "")


def _llamar_claude(modelo: str, contenido: list) -> dict:
    try:
        resp = _cliente().messages.create(
            model=modelo,
            max_tokens=1024,
            system=INSTRUCCIONES,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": contenido}],
        )
    except IANoDisponible:
        raise
    except anthropic.APITimeoutError as e:
        raise IANoDisponible("Tiempo de espera agotado") from e
    except anthropic.APIError as e:
        log.warning("Fallo de la API de Claude: %s", type(e).__name__)
        raise IANoDisponible(str(type(e).__name__)) from e
    if resp.stop_reason == "refusal":
        return {"categoria": "DESCONOCIDO", "objeto": "", "confianza": "baja"}
    texto = "".join(b.text for b in resp.content if b.type == "text")
    return interpretar(texto)


def interpretar(texto: str) -> dict:
    """Extrae el JSON de la respuesta, tolerando texto extra."""
    m = re.search(r"\{.*\}", texto or "", re.S)
    try:
        datos = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        datos = {}
    cat = str(datos.get("categoria", "DESCONOCIDO")).upper()
    conf = str(datos.get("confianza", "baja")).lower()
    return {
        "categoria": cat if cat in CATEGORIAS else "DESCONOCIDO",
        "objeto": str(datos.get("objeto", "")).strip()[:80],
        "confianza": conf if conf in {"alta", "media", "baja"} else "baja",
    }


def clasificar_texto(descripcion: str) -> dict:
    return _llamar(config().ia_modelo_texto, [{"type": "text", "text": f"Residuo: {descripcion[:500]}"}])


def clasificar_imagen(jpeg: bytes) -> dict:
    return _llamar(config().ia_modelo_vision, [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(jpeg).decode("ascii")}},
        {"type": "text", "text": "Clasifica el residuo de la foto."},
    ])

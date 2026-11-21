"""Notas de voz de WhatsApp a texto con Azure OpenAI (whisper o gpt-4o-mini-transcribe).

Idea tomada del bot de `chatbot/transcripcion.py` (otro integrante del equipo), pero con un
proveedor autorizado por el reto (sección 8): Azure OpenAI con el SDK oficial de OpenAI.
Se activa con AZURE_OPENAI_STT_DEPLOYMENT. El audio no se guarda: se transcribe en memoria.
"""
import io
import logging

from ..config import config
from .modelo import IANoDisponible

log = logging.getLogger("ecoconecta.ia")
MAX_BYTES = 10 * 1024 * 1024  # una nota de voz de WhatsApp pesa mucho menos
EXTENSION = {"audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/aac": "m4a",
             "audio/amr": "amr", "audio/wav": "wav", "audio/webm": "webm"}


def disponible() -> bool:
    cfg = config()
    return bool(cfg.azure_openai_stt_deployment and cfg.azure_openai_endpoint and cfg.azure_openai_api_key)


def transcribir(datos: bytes, mime: str = "audio/ogg") -> str:
    """Devuelve el texto del audio (puede ser vacío). Lanza IANoDisponible si falla."""
    if not disponible():
        raise IANoDisponible("Falta AZURE_OPENAI_STT_DEPLOYMENT")
    if not datos or len(datos) > MAX_BYTES:
        raise IANoDisponible("Audio vacío o demasiado grande")
    import openai
    cfg = config()
    archivo = io.BytesIO(datos)
    archivo.name = "nota." + EXTENSION.get(mime.split(";")[0].strip(), "ogg")
    try:
        cliente = openai.AzureOpenAI(azure_endpoint=cfg.azure_openai_endpoint, api_key=cfg.azure_openai_api_key,
                                     api_version=cfg.azure_openai_api_version, timeout=cfg.ia_timeout_s,
                                     max_retries=1)
        r = cliente.audio.transcriptions.create(model=cfg.azure_openai_stt_deployment, file=archivo, language="es")
    except openai.APIError as e:
        log.warning("Fallo de la transcripción en Azure OpenAI: %s", type(e).__name__)
        raise IANoDisponible(type(e).__name__) from e
    return " ".join((getattr(r, "text", "") or "").split())[:1000]

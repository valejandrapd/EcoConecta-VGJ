"""Audio -> texto con un servicio de transcripción compatible con la API de OpenAI (/audio/transcriptions).

Claude no recibe audio, así que se transcribe aparte y el texto sigue el flujo normal (se segmenta y se confirma).
Variables:  STT_API_KEY (obligatoria; sin ella el bot responde que aún no entiende audios)
            STT_URL    (por defecto Groq: https://api.groq.com/openai/v1/audio/transcriptions;
                        OpenAI: https://api.openai.com/v1/audio/transcriptions)
            STT_MODEL  (por defecto whisper-large-v3-turbo; con OpenAI: whisper-1)
            STT_LANGUAGE (por defecto es)
⚠️ El audio de la persona se envía a ese proveedor: avisar en la política de datos del proyecto.
"""
import json
import os
import urllib.request
import uuid

URL_POR_DEFECTO = "https://api.groq.com/openai/v1/audio/transcriptions"
EXTENSIONES = {"ogg": "ogg", "opus": "ogg", "mpeg": "mp3", "mp3": "mp3", "mp4": "m4a", "m4a": "m4a",
               "aac": "m4a", "webm": "webm", "wav": "wav", "x-wav": "wav", "flac": "flac"}


def configurada() -> bool:
    return bool(os.environ.get("STT_API_KEY"))


def _extension(mime: str) -> str:
    sub = (mime or "").split(";")[0].split("/")[-1].lower()
    return EXTENSIONES.get(sub, "ogg")


def transcribir(audio: bytes, mime: str = "audio/ogg") -> str:
    """Devuelve el texto del audio ("" si no se entiende nada)."""
    limite = "----eco" + uuid.uuid4().hex
    campos = {"model": os.environ.get("STT_MODEL", "whisper-large-v3-turbo"),
              "language": os.environ.get("STT_LANGUAGE", "es"), "response_format": "json", "temperature": "0"}
    cuerpo = b""
    for k, v in campos.items():
        cuerpo += f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    cuerpo += (f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="audio.{_extension(mime)}"\r\n'
               f'Content-Type: {(mime or "audio/ogg").split(";")[0]}\r\n\r\n').encode() + audio + f"\r\n--{limite}--\r\n".encode()
    req = urllib.request.Request(
        os.environ.get("STT_URL", URL_POR_DEFECTO), data=cuerpo,
        headers={"Authorization": "Bearer " + os.environ["STT_API_KEY"], "Accept": "application/json",
                 "Content-Type": f"multipart/form-data; boundary={limite}", "User-Agent": "ecoconecta-chatbot/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return str(json.loads(r.read() or b"{}").get("text", "")).strip()

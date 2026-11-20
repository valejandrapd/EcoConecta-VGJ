"""Validación de la firma X-Hub-Signature-256 que Meta añade a cada POST del webhook."""
import hashlib
import hmac


def firma_valida(cuerpo: bytes, cabecera: str | None, app_secret: str) -> bool:
    if not app_secret or not cabecera or not cabecera.startswith("sha256="):
        return False
    esperada = hmac.new(app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, cabecera.removeprefix("sha256="))


def firmar(cuerpo: bytes, app_secret: str) -> str:
    """Genera la cabecera (para pruebas y para el simulador local)."""
    return "sha256=" + hmac.new(app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()

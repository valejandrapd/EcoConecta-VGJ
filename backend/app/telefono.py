"""Normalización de teléfonos a E.164 (+573001234567)."""
import re

from .config import config


def normalizar(numero: str, pais: str | None = None) -> str:
    """Devuelve el número en E.164 o "" si no es válido.

    Acepta "+57 300 123 4567", "573001234567" (formato wa_id de Meta) o "3001234567" (nacional).
    """
    if not numero:
        return ""
    pais = pais or config().pais_telefono
    crudo = str(numero).strip()
    digitos = re.sub(r"\D", "", crudo)
    if not digitos:
        return ""
    if crudo.startswith("+") or crudo.startswith("00"):
        digitos = digitos[2:] if crudo.startswith("00") else digitos
    elif len(digitos) == 10 and pais == "57":
        digitos = pais + digitos  # número nacional colombiano
    if not 8 <= len(digitos) <= 15:
        return ""
    return "+" + digitos

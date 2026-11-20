"""Autenticación mínima con la librería estándar: claves con scrypt y tokens firmados con HMAC.

Token: base64url(json {"uid", "exp"}) + "." + base64url(hmac_sha256(AUTH_SECRET, payload)).
"""
import base64
import hashlib
import hmac
import json
import os
import time

from .config import config


class TokenInvalido(ValueError):
    pass


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_clave(clave: str) -> str:
    sal = os.urandom(16)
    h = hashlib.scrypt(clave.encode(), salt=sal, n=2 ** 14, r=8, p=1)
    return f"scrypt${_b64(sal)}${_b64(h)}"


def verificar_clave(clave: str, guardado: str | None) -> bool:
    if not guardado or not guardado.startswith("scrypt$"):
        return False
    _, sal, h = guardado.split("$")
    calculado = hashlib.scrypt(clave.encode(), salt=_unb64(sal), n=2 ** 14, r=8, p=1)
    return hmac.compare_digest(calculado, _unb64(h))


def _secreto() -> bytes:
    s = config().auth_secret
    if len(s) < 16:
        raise RuntimeError("AUTH_SECRET debe tener al menos 16 caracteres")
    return s.encode()


def crear_token(usuario_id: int) -> str:
    carga = _b64(json.dumps({"uid": usuario_id, "exp": int(time.time()) + config().sesion_horas * 3600}).encode())
    firma = _b64(hmac.new(_secreto(), carga.encode(), hashlib.sha256).digest())
    return f"{carga}.{firma}"


def leer_token(token: str) -> int:
    try:
        carga, firma = token.split(".")
        esperada = _b64(hmac.new(_secreto(), carga.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            raise TokenInvalido("firma")
        datos = json.loads(_unb64(carga))
    except (ValueError, json.JSONDecodeError) as e:
        raise TokenInvalido("formato") from e
    if datos.get("exp", 0) < time.time():
        raise TokenInvalido("vencido")
    return int(datos["uid"])

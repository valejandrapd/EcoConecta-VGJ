"""API REST de EcoConecta para apps móviles y sitios web.

Se monta en la misma app Flask que el webhook de WhatsApp (ver `app.py`), bajo `/api/v1`.

Variables de entorno (todas opcionales):
    API_KEY         si se define, cada petición debe traer la cabecera `X-API-Key: <valor>`
    CORS_ORIGINS    orígenes web permitidos, separados por coma (p. ej. https://miweb.com) o `*`
    MAX_FOTO_MB     tamaño máximo de la foto (por defecto 8)

Endpoints:
    POST /api/v1/solicitudes                  JSON {"contacto","texto"}  ó  multipart (contacto + foto)
    POST /api/v1/solicitudes/<codigo>/foto    multipart: foto=<archivo>
    GET  /api/v1/solicitudes/<codigo>
    GET  /api/v1/solicitudes?contacto=...&limite=50
"""
import hmac
import logging
import os

from flask import Blueprint, jsonify, request

import core
import vision

log = logging.getLogger("ecoconecta.api")
bp = Blueprint("api", __name__, url_prefix="/api/v1")


def max_foto_bytes():
    return int(float(os.environ.get("MAX_FOTO_MB", "8")) * 1024 * 1024)


def _error(codigo_http, mensaje):
    return jsonify(error=mensaje), codigo_http


@bp.before_request
def _autenticar():
    if request.method == "OPTIONS":
        return None  # preflight de CORS
    clave = os.environ.get("API_KEY")
    if clave and not hmac.compare_digest(request.headers.get("X-API-Key", ""), clave):
        return _error(401, "API key inválida o ausente (cabecera X-API-Key).")
    return None


@bp.after_request
def _cors(resp):
    permitidos = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    origen = request.headers.get("Origin", "")
    if permitidos and ("*" in permitidos or origen in permitidos):
        resp.headers["Access-Control-Allow-Origin"] = "*" if "*" in permitidos else origen
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@bp.route("/solicitudes", methods=["OPTIONS"])
@bp.route("/solicitudes/<path:_>", methods=["OPTIONS"])
def _preflight(_=None):
    return "", 204


def _leer_foto():
    """Devuelve (bytes, mime) del campo multipart `foto`, o None si no vino."""
    archivo = request.files.get("foto")
    if not archivo:
        return None
    datos = archivo.read(max_foto_bytes() + 1)
    if len(datos) > max_foto_bytes():
        raise core.DatosInvalidos(f"La foto supera el máximo de {os.environ.get('MAX_FOTO_MB', '8')} MB.")
    return datos, (archivo.mimetype or "").lower()


def _clasificar(datos, mime):
    return vision.clasificar_foto(datos, mime)


@bp.post("/solicitudes")
def crear_solicitud():
    try:
        if request.is_json:
            cuerpo = request.get_json(silent=True) or {}
            r = core.registrar_texto(cuerpo.get("contacto"), cuerpo.get("texto"), canal=cuerpo.get("canal") or "api")
            return jsonify(r), 201
        # multipart: contacto (+ foto, y opcionalmente texto)
        contacto, texto = request.form.get("contacto"), request.form.get("texto")
        canal = request.form.get("canal") or "api"
        foto = _leer_foto()
        if texto and texto.strip():
            r = core.registrar_texto(contacto, texto, canal=canal)
            if r["necesita_foto"] and foto:
                r = core.adjuntar_foto(contacto, *foto, _clasificar, canal=canal, codigo=r["codigo"])
            return jsonify(r), 201
        if foto:
            return jsonify(core.adjuntar_foto(contacto, *foto, _clasificar, canal=canal)), 201
        raise core.DatosInvalidos("Envía `texto` (JSON o formulario) y/o una `foto` (multipart).")
    except core.DatosInvalidos as e:
        return _error(400, str(e))
    except Exception:  # noqa: BLE001 - fallo del proveedor de IA, red, etc.
        log.exception("Error creando la solicitud")
        return _error(502, "No se pudo identificar el residuo en este momento. Intenta de nuevo.")


@bp.post("/solicitudes/<codigo>/foto")
def enviar_foto(codigo):
    try:
        foto = _leer_foto()
        if not foto:
            raise core.DatosInvalidos("Falta el archivo `foto` (multipart/form-data).")
        r = core.adjuntar_foto(request.form.get("contacto"), *foto, _clasificar, codigo=codigo)
        return jsonify(r)
    except core.SolicitudNoEncontrada:
        return _error(404, "No existe esa solicitud.")
    except core.DatosInvalidos as e:
        return _error(400, str(e))
    except Exception:  # noqa: BLE001
        log.exception("Error procesando la foto de %s", codigo)
        return _error(502, "No se pudo identificar el residuo en este momento. Intenta de nuevo.")


@bp.get("/solicitudes/<codigo>")
def ver_solicitud(codigo):
    try:
        return jsonify(core.consultar(codigo))
    except core.SolicitudNoEncontrada:
        return _error(404, "No existe esa solicitud.")


@bp.get("/solicitudes")
def listar_solicitudes():
    try:
        limite = int(request.args.get("limite", 50))
    except ValueError:
        return _error(400, "`limite` debe ser un número.")
    return jsonify(core.listar(request.args.get("contacto"), limite))

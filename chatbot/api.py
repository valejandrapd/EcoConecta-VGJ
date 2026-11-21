"""API REST /api/v1 de EcoConecta: sirve al bot, a la app y a la web, y define el CONTRATO que debe cumplir el backend real.

Variables opcionales:  API_KEY (cabecera X-API-Key) · CORS_ORIGINS · MAX_FOTO_MB

  POST /clasificar                       texto o foto -> categoría sugerida (sin guardar nada)
  POST /segmentar                        texto, foto o audio con VARIOS residuos -> cada uno con su tipo (sin guardar nada)
  POST /solicitudes                      crea la solicitud y la enruta (huerteros | recicladores)
  GET  /solicitudes/<codigo>[?contacto=] detalle + historial (con `contacto`, solo si es suya)
  GET  /solicitudes?contacto=&flujo=&estado=&limite=
  GET  /puntos/<contacto>                puntos acumulados
  POST /notificar                        {"codigo"} avisa al usuario por WhatsApp del estado actual

  [PROVISIONAL – lo hace el panel del coordinador/recolector en el backend real]
  POST /solicitudes/<codigo>/asignar     {"coordinador","recolector"}
  POST /solicitudes/<codigo>/programar   {"dia","hora","recolector"?}
  POST /solicitudes/<codigo>/recolectar  {"cantidad_kg"}
  POST /solicitudes/<codigo>/cancelar    {"motivo"}
Las acciones provisionales avisan solas al usuario por WhatsApp.
"""
import hmac
import logging
import os

from flask import Blueprint, jsonify, request

import core
import notificar
import transcripcion
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
        return None
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


@bp.errorhandler(core.SolicitudNoEncontrada)
def _no_existe(_):
    return _error(404, "No existe esa solicitud.")


@bp.errorhandler(core.DatosInvalidos)
def _invalido(e):
    return _error(400, str(e))


@bp.errorhandler(core.TransicionInvalida)
def _transicion(e):
    return _error(409, str(e))


def _cuerpo():
    return request.get_json(silent=True) or {}


def _leer_foto():
    archivo = request.files.get("foto")
    if not archivo:
        return None
    datos = archivo.read(max_foto_bytes() + 1)
    if len(datos) > max_foto_bytes():
        raise core.DatosInvalidos(f"La foto supera el máximo de {os.environ.get('MAX_FOTO_MB', '8')} MB.")
    return datos, (archivo.mimetype or "").lower()


def _leer_audio():
    archivo = request.files.get("audio")
    if not archivo:
        return None
    datos = archivo.read(max_foto_bytes() + 1)
    if len(datos) > max_foto_bytes():
        raise core.DatosInvalidos(f"El audio supera el máximo de {os.environ.get('MAX_FOTO_MB', '8')} MB.")
    return datos, (archivo.mimetype or "audio/ogg").lower()


def _avisar(s):
    """Avisa por WhatsApp; si falla el envío no se deshace el cambio de estado."""
    try:
        notificar.notificar(s["codigo"])
    except Exception:  # noqa: BLE001
        log.exception("No se pudo notificar la solicitud %s", s["codigo"])
    return s


@bp.post("/clasificar")
def clasificar():
    texto = request.form.get("texto") if request.files or request.form else _cuerpo().get("texto")
    foto = _leer_foto()
    try:
        if foto:
            return jsonify(core.clasificar(texto, foto[0], foto[1], vision.clasificar_foto))
        return jsonify(core.clasificar(texto))
    except (core.DatosInvalidos, core.SolicitudNoEncontrada):
        raise
    except Exception:  # noqa: BLE001 - fallo del proveedor de IA, red, etc.
        log.exception("Error clasificando")
        return _error(502, "No se pudo identificar el residuo en este momento. Intenta de nuevo.")


@bp.post("/segmentar")
def segmentar():
    """Separa varios residuos y los agrupa por tipo (cada tipo = un colectivo = una solicitud al crearla).
    Multipart o JSON con `texto`, `foto` (JPG/PNG/WEBP/GIF) o `audio` (se transcribe y se devuelve en `transcripcion`)."""
    form = request.form if request.files or request.form else _cuerpo()
    texto, foto, audio = form.get("texto"), _leer_foto(), _leer_audio()
    try:
        transcrito = None
        if audio:
            if not transcripcion.configurada():
                return _error(503, "La transcripción de audio no está configurada (falta STT_API_KEY).")
            transcrito = transcripcion.transcribir(*audio)
            if not transcrito:
                raise core.DatosInvalidos("No se entendió el audio. Intenta de nuevo o envía el texto.")
            texto = transcrito
        if foto:
            r = core.segmentar(imagen=foto[0], mime=foto[1], segmentar_foto=vision.segmentar_foto)
        else:
            r = core.segmentar(texto=texto)
        if transcrito is not None:
            r["metodo"], r["transcripcion"] = "audio", transcrito
        return jsonify(r)
    except (core.DatosInvalidos, core.SolicitudNoEncontrada):
        raise
    except Exception:  # noqa: BLE001 - fallo del proveedor de IA / transcripción, red, etc.
        log.exception("Error segmentando")
        return _error(502, "No se pudo analizar el residuo en este momento. Intenta de nuevo.")


@bp.post("/solicitudes")
def crear():
    s = core.crear_solicitud(_cuerpo())
    return jsonify(_avisar(s) if s.get("canal") == "whatsapp" else s), 201


@bp.get("/solicitudes/<codigo>")
def ver(codigo):
    return jsonify(core.consultar(codigo, request.args.get("contacto"), con_historial=True))


@bp.get("/solicitudes")
def listar():
    try:
        limite = int(request.args.get("limite", 50))
    except ValueError:
        return _error(400, "`limite` debe ser un número.")
    return jsonify(core.listar(request.args.get("contacto"), request.args.get("flujo"),
                               request.args.get("estado"), limite))


@bp.get("/puntos/<contacto>")
def puntos(contacto):
    return jsonify(contacto=contacto, puntos=core.puntos(contacto))


@bp.post("/notificar")
def avisar():
    codigo = _cuerpo().get("codigo")
    if not codigo:
        raise core.DatosInvalidos("Falta `codigo`.")
    texto = notificar.notificar(codigo)
    return jsonify(enviado=bool(texto))


@bp.post("/solicitudes/<codigo>/asignar")
def asignar(codigo):
    b = _cuerpo()
    return jsonify(_avisar(core.asignar(codigo, b.get("coordinador"), b.get("recolector"))))


@bp.post("/solicitudes/<codigo>/programar")
def programar(codigo):
    b = _cuerpo()
    return jsonify(_avisar(core.programar(codigo, b.get("dia"), b.get("hora"), b.get("recolector"), b.get("actor"))))


@bp.post("/solicitudes/<codigo>/recolectar")
def recolectar(codigo):
    b = _cuerpo()
    return jsonify(_avisar(core.recolectar(codigo, b.get("cantidad_kg"), b.get("actor"))))


@bp.post("/solicitudes/<codigo>/cancelar")
def cancelar(codigo):
    b = _cuerpo()
    return jsonify(_avisar(core.cancelar(codigo, b.get("motivo", ""), b.get("actor"))))

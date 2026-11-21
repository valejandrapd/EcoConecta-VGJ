"""Lógica de negocio de EcoConecta, independiente del canal (WhatsApp, app o web).

⚠️ PROVISIONAL: esto es un backend mínimo para que el chatbot funcione de punta a punta mientras el equipo
construye el backend real. Las reglas (RN-xx) siguen el reto oficial. Si el backend real expone la misma
API (ver docs/CONTRATO_BACKEND.md), el chatbot lo usa con la variable BACKEND_URL y este módulo deja de usarse.

Reglas que implementa:
  RN-01 cada solicitud se clasifica (ORGANICO | RECICLABLE) y va al flujo huerteros | recicladores
  RN-02 no está `programada` hasta registrar día, hora y persona encargada
  RN-03 la atención queda asociada a coordinador y recolector
  RN-04 cada cambio de estado queda en el historial
  RN-05 los puntos solo se asignan al registrar la recolección
  RN-06 los puntos salen de una regla PARAMETRIZABLE (variables PUNTOS_BASE y PUNTOS_POR_KG);
        los valores por defecto son de demostración y NO son oficiales de la Fundación
"""
import os

import db
import segmentar as _seg
from clasificador import clasificar_texto

CATEGORIAS = ("ORGANICO", "RECICLABLE")
FLUJOS = {"ORGANICO": "huerteros", "RECICLABLE": "recicladores"}
GENERADORES = ("hogar", "negocio")
MIMES_IMAGEN = ("image/jpeg", "image/png", "image/webp", "image/gif")
ESTADOS = ("recibida", "en_revision", "asignada", "programada", "recolectada", "cancelada")
ESTADOS_CERRADOS = ("recolectada", "cancelada")


class SolicitudNoEncontrada(LookupError):
    """El código de solicitud no existe."""


class DatosInvalidos(ValueError):
    """Entrada incompleta o no válida."""


class TransicionInvalida(ValueError):
    """La solicitud no puede pasar a ese estado desde el actual."""


def _limpio(v):
    return str(v).strip() if v is not None else ""


def _vista(fila, con_historial=False):
    if not fila:
        return None
    v = dict(fila)
    v["programacion"] = {"dia": v["dia"], "hora": v["hora"], "recolector": v["recolector"]} \
        if v.get("dia") and v.get("hora") and v.get("recolector") else None
    if con_historial:
        v["historial"] = db.historial_de(v["codigo"])
    return v


# ---- clasificación (sin estado: no guarda nada)
def clasificar(texto=None, imagen=None, mime=None, clasificar_foto=None):
    """Texto o foto -> {categoria, metodo, objeto, necesita_foto, foto_ilegible}. Orientativa: la confirma una persona."""
    if texto and texto.strip():
        cat = clasificar_texto(texto)
        if cat:
            return {"categoria": cat, "metodo": "texto", "objeto": "", "necesita_foto": False, "foto_ilegible": False}
        if imagen is None:
            return {"categoria": None, "metodo": None, "objeto": "", "necesita_foto": True, "foto_ilegible": False}
    if imagen is None:
        raise DatosInvalidos("Envía `texto` y/o una `foto`.")
    if mime not in MIMES_IMAGEN:
        raise DatosInvalidos(f"Tipo de imagen no soportado ({mime}). Usa JPG, PNG, WEBP o GIF.")
    categoria, objeto = clasificar_foto(imagen, mime)
    if categoria not in CATEGORIAS + ("OTRO",):
        return {"categoria": None, "metodo": "foto", "objeto": "", "necesita_foto": True, "foto_ilegible": True}
    return {"categoria": categoria, "metodo": "foto", "objeto": objeto, "necesita_foto": False, "foto_ilegible": False}


def segmentar(texto=None, imagen=None, mime=None, segmentar_foto=None):
    """Texto o foto -> varios residuos, cada uno con su tipo (un tipo = un colectivo = una solicitud).
    {"items": [{"objeto","categoria"}], "grupos": {"ORGANICO": [...], "RECICLABLE": [...], "OTRO": [...], "DUDA": [...]},
     "metodo": "texto" | "foto"}. `categoria` DUDA = hay que preguntarle a la persona. Orientativo: lo confirma una persona."""
    if imagen is not None:
        if mime not in MIMES_IMAGEN:
            raise DatosInvalidos(f"Tipo de imagen no soportado ({mime}). Usa JPG, PNG, WEBP o GIF.")
        crudo = segmentar_foto(imagen, mime)
        if isinstance(crudo, tuple):  # clasificador de un solo residuo: (categoria, objeto)
            crudo = [crudo]
        items = [{"objeto": (o or "residuo").strip(), "categoria": c if c in CATEGORIAS + ("OTRO",) else "DUDA"}
                 for c, o in crudo if c != "NO_SE_VE"]
        metodo = "foto"
    elif texto and texto.strip():
        items, metodo = _seg.segmentar_texto(texto.strip()), "texto"
    else:
        raise DatosInvalidos("Envía `texto` y/o una `foto`.")
    return {"items": items, "grupos": _seg.agrupar(items), "metodo": metodo}


# ---- solicitudes
def crear_solicitud(datos: dict):
    """Crea la solicitud y la enruta al flujo correcto. Campos mínimos del reto (5.3):
    contacto, direccion, generador, categoria, disponibilidad; observaciones es opcional."""
    d = {k: _limpio(datos.get(k)) for k in (
        "contacto", "canal", "generador", "categoria", "objeto", "metodo", "direccion", "disponibilidad", "observaciones")}
    d["categoria"] = d["categoria"].upper()
    d["generador"] = d["generador"].lower()
    d["canal"] = d["canal"] or "api"
    falta = [k for k in ("contacto", "direccion", "generador", "categoria", "disponibilidad") if not d[k]]
    if falta:
        raise DatosInvalidos("Faltan datos: " + ", ".join(falta))
    if d["categoria"] not in CATEGORIAS:
        raise DatosInvalidos("`categoria` debe ser ORGANICO o RECICLABLE.")
    if d["generador"] not in GENERADORES:
        raise DatosInvalidos("`generador` debe ser hogar o negocio.")
    d["flujo"] = FLUJOS[d["categoria"]]
    return consultar(db.crear_solicitud(d), con_historial=True)


def consultar(codigo, contacto=None, con_historial=False):
    """Con `contacto`, solo devuelve la solicitud si es suya (RN-07 privacidad)."""
    fila = db.obtener(codigo)
    if not fila or (contacto and fila["contacto"] != str(contacto)):
        raise SolicitudNoEncontrada(codigo)
    return _vista(fila, con_historial)


def listar(contacto=None, flujo=None, estado=None, limite=50):
    return [_vista(f) for f in db.listar(contacto, flujo, estado, limite)]


def _abierta(codigo):
    s = consultar(codigo)
    if s["estado"] in ESTADOS_CERRADOS:
        raise TransicionInvalida(f"La solicitud ya está {s['estado']}.")
    return s


def asignar(codigo, coordinador, recolector):
    """RN-03: la atención queda asociada a un coordinador y a un recolector del colectivo."""
    if not _limpio(coordinador) or not _limpio(recolector):
        raise DatosInvalidos("Faltan `coordinador` y `recolector`.")
    _abierta(codigo)
    db.actualizar(codigo, "asignada", actor=coordinador, detalle=f"Asignada a {recolector}",
                  coordinador=_limpio(coordinador), recolector=_limpio(recolector))
    return consultar(codigo, con_historial=True)


def programar(codigo, dia, hora, recolector=None, actor=None):
    """RN-02: solo queda `programada` con día, hora y persona encargada."""
    s = _abierta(codigo)
    persona = _limpio(recolector) or s["recolector"]
    if not _limpio(dia) or not _limpio(hora) or not persona:
        raise DatosInvalidos("Para programar se requieren `dia`, `hora` y persona encargada (`recolector`).")
    db.actualizar(codigo, "programada", actor=actor or s["coordinador"] or "coordinador",
                  detalle=f"{_limpio(dia)} {_limpio(hora)} con {persona}",
                  dia=_limpio(dia), hora=_limpio(hora), recolector=persona)
    return consultar(codigo, con_historial=True)


def calcular_puntos(cantidad_kg):
    """RN-06: regla parametrizable (valores de demostración, no oficiales)."""
    base = int(os.environ.get("PUNTOS_BASE", "10"))
    por_kg = float(os.environ.get("PUNTOS_POR_KG", "2"))
    return base + int(round(por_kg * float(cantidad_kg or 0)))


def recolectar(codigo, cantidad_kg=None, actor=None):
    """RN-05: registra la recolección; solo entonces se asignan los puntos (solo si estaba programada)."""
    s = _abierta(codigo)
    if s["estado"] != "programada":
        raise TransicionInvalida("Solo se registra la recolección de una solicitud programada (con día, hora y persona).")
    try:
        kg = float(cantidad_kg) if cantidad_kg not in (None, "") else None
    except (TypeError, ValueError):
        raise DatosInvalidos("`cantidad_kg` debe ser un número.") from None
    if kg is not None and kg < 0:
        raise DatosInvalidos("`cantidad_kg` no puede ser negativa.")
    puntos = calcular_puntos(kg)
    db.actualizar(codigo, "recolectada", actor=actor or s["recolector"],
                  detalle=f"Recolección registrada ({kg if kg is not None else 's/d'} kg), +{puntos} puntos",
                  cantidad_kg=kg, puntos=puntos)
    return consultar(codigo, con_historial=True)


def cancelar(codigo, motivo="", actor=None):
    _abierta(codigo)
    db.actualizar(codigo, "cancelada", actor=actor or "usuario", detalle=_limpio(motivo) or "Cancelada")
    return consultar(codigo, con_historial=True)


def puntos(contacto):
    return db.puntos_de(_limpio(contacto))

"""Núcleo de EcoConecta: clasifica residuos y gestiona solicitudes, SIN depender de ningún canal.

Lo usan por igual el bot de WhatsApp (`bot.py`), la API REST (`api.py`) y cualquier app/web que
importe este módulo directamente. No envía mensajes ni conoce HTTP: recibe datos y devuelve dicts.

Resultado (dict) que devuelven las funciones:
    codigo        RES-AAAAMMDD-NNNN
    estado        "resuelta" | "esperando_foto"
    categoria     "ORGANICO" | "RECICLABLE" | "OTRO" | None (si aún falta la foto)
    metodo        "texto" | "foto" | None
    objeto        nombre del residuo (solo si se identificó por foto)
    necesita_foto True si hay que enviar (o reenviar) una foto
    foto_ilegible True si la última foto no permitió distinguir el residuo
"""
import db
from clasificador import clasificar_texto

CATEGORIAS = ("ORGANICO", "RECICLABLE", "OTRO")
MIMES_IMAGEN = ("image/jpeg", "image/png", "image/webp", "image/gif")


class SolicitudNoEncontrada(LookupError):
    """El código de solicitud no existe."""


class DatosInvalidos(ValueError):
    """Entrada vacía o de un tipo no soportado."""


def _resultado(fila, foto_ilegible=False):
    pendiente = fila["estado"] != "resuelta"
    return {
        "codigo": fila["codigo"],
        "estado": fila["estado"],
        "categoria": fila["categoria"],
        "metodo": fila["metodo"],
        "objeto": fila.get("objeto") or "",
        "descripcion": fila.get("descripcion") or "",
        "contacto": fila["contacto"],
        "canal": fila.get("canal") or "",
        "creada": fila["creada"],
        "necesita_foto": pendiente,
        "foto_ilegible": foto_ilegible and pendiente,
    }


def registrar_texto(contacto, texto, canal="api"):
    """Crea una solicitud con ID único; si el texto alcanza, la resuelve. Si no, queda esperando foto."""
    texto = (texto or "").strip()
    contacto = str(contacto or "").strip()
    if not texto:
        raise DatosInvalidos("Falta el texto con la descripción del residuo.")
    if not contacto:
        raise DatosInvalidos("Falta el contacto (usuario, teléfono o correo de quien pide).")
    codigo = db.crear(contacto, texto, canal)
    categoria = clasificar_texto(texto)
    if categoria:
        db.resolver(codigo, categoria, "texto")
    return _resultado(db.obtener(codigo))


def adjuntar_foto(contacto, imagen, mime, clasificar_foto, canal="api", codigo=None):
    """Identifica el residuo por foto.

    Con `codigo` resuelve esa solicitud; sin él, usa la última pendiente del contacto o crea una nueva.
    `clasificar_foto(bytes, mime) -> (categoria, objeto)` se inyecta (normalmente `vision.clasificar_foto`).
    Si falla la clasificación la excepción se propaga y la solicitud queda pendiente.
    """
    if not imagen:
        raise DatosInvalidos("La imagen está vacía.")
    if mime not in MIMES_IMAGEN:
        raise DatosInvalidos(f"Tipo de imagen no soportado ({mime}). Usa JPG, PNG, WEBP o GIF.")
    contacto = str(contacto or "").strip()

    if codigo:
        fila = db.obtener(codigo)
        if not fila:
            raise SolicitudNoEncontrada(codigo)
        if fila["estado"] == "resuelta":
            return _resultado(fila)  # ya estaba resuelta: no se vuelve a gastar una llamada a la IA
    else:
        if not contacto:
            raise DatosInvalidos("Falta el contacto (usuario, teléfono o correo de quien pide).")
        fila = db.pendiente_de_foto(contacto)
        if not fila:
            db.crear(contacto, "(solo foto)", canal)
            fila = db.pendiente_de_foto(contacto)

    categoria, objeto = clasificar_foto(imagen, mime)
    if categoria not in CATEGORIAS:  # NO_SE_VE u otro valor inesperado
        return _resultado(fila, foto_ilegible=True)
    db.resolver(fila["codigo"], categoria, "foto", objeto)
    return _resultado(db.obtener(fila["codigo"]))


def consultar(codigo):
    fila = db.obtener(codigo)
    if not fila:
        raise SolicitudNoEncontrada(codigo)
    return _resultado(fila)


def listar(contacto=None, limite=50):
    return [_resultado(f) for f in db.listar(contacto, limite)]

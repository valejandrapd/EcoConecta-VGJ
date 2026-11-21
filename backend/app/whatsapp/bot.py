"""Lógica de conversación del bot de WhatsApp.

Se ejecuta en segundo plano (BackgroundTasks) después de que el webhook ya respondió 200.
Identidad: el `wa_id` se normaliza a E.164 y se busca en `usuarios.telefono`.
"""
import logging
import re
from datetime import date

from sqlalchemy import select

from .. import telefono
from ..config import config
from ..db import sesion
from ..ia import cascada
from ..ia.imagen import ImagenInvalida
from ..ia.modelo import IANoDisponible
from ..ia.reglas import normalizar
from ..models import CasoCoordinacion, Contenido, ConversacionWhatsapp, Solicitud, Usuario
from . import solicitud_bot, textos
from .cliente import ErrorWhatsApp, obtener_cliente
from .mensajeria import entrantes_hoy, enviar, marcar_intencion

log = logging.getLogger("ecoconecta.bot")

RE_CODIGO = re.compile(r"\b(ORG|REC)\s*-?\s*(\d{1,6})\b", re.I)
MENU = {"hola", "menu", "inicio", "ayuda", "buenas", "buenos dias", "buenas tardes", "0", "hi"}
PIDE_PERSONA = ("persona", "humano", "asesor", "coordinador", "coordinacion", "hablar con", "agente")
DUDA = ("organico", "reciclable", "donde boto", "donde va", "donde echo", "que tipo", "en que caneca",
        "como separo", "se recicla", "es reciclable", "es organico")
TIPOS_CONTENIDO = {"horario": "horario", "horarios": "horario", "ruta": "ruta", "rutas": "ruta",
                   "tutorial": "tutorial", "separar": "tutorial", "separo": "tutorial"}


class Respuesta:
    def __init__(self, texto: str, intencion: str, entendido: bool = True):
        self.texto, self.intencion, self.entendido = texto, intencion, entendido


def procesar(mensaje: dict):
    """Atiende UN mensaje entrante de Meta (`value.messages[i]`). Nunca lanza."""
    try:
        with sesion() as s:
            _procesar(s, mensaje)
    except Exception:  # noqa: BLE001 - un fallo no debe tumbar el worker
        log.exception("Error atendiendo el mensaje %s", mensaje.get("id"))


def _procesar(s, mensaje: dict):
    wa_id = mensaje.get("from", "")
    usuario = s.scalar(select(Usuario).where(Usuario.telefono == telefono.normalizar(wa_id),
                                             Usuario.activo.is_(True)))
    conv = s.get(ConversacionWhatsapp, wa_id) or ConversacionWhatsapp(wa_id=wa_id, fallos_seguidos=0)
    s.add(conv)
    uid = usuario.id if usuario else None

    # Control de abuso: límite diario por número (un solo aviso por día)
    if entrantes_hoy(s, wa_id) > config().limite_mensajes_dia:
        if conv.aviso_limite_en != date.today():
            conv.aviso_limite_en = date.today()
            enviar(s, wa_id, texto=textos.LIMITE.format(url=textos.enlace_formulario()),
                   intencion="limite", usuario_id=uid)
        return

    tipo = mensaje.get("type")
    if tipo == "text":
        r = _texto(s, (mensaje.get("text") or {}).get("body", ""), usuario, conv)
    elif tipo == "image":
        r = _imagen(s, mensaje.get("image") or {}, usuario, conv)
    else:
        r = Respuesta(textos.SOLO_TEXTO_FOTO, "no_soportado")

    if r.entendido:
        conv.fallos_seguidos = 0
    else:
        conv.fallos_seguidos = (conv.fallos_seguidos or 0) + 1
        if conv.fallos_seguidos >= 2:
            r = _derivar(s, usuario, conv, "no_entendido", "(el bot no entendió dos veces seguidas)")
            conv.fallos_seguidos = 0
    marcar_intencion(s, mensaje.get("id"), r.intencion)
    enviar(s, wa_id, texto=r.texto, intencion=r.intencion, usuario_id=uid)


# ---------------------------------------------------------------- texto
def _texto(s, cuerpo: str, usuario, conv) -> Respuesta:
    t = normalizar(cuerpo)
    if not t or t in MENU:
        conv.estado = None
        solicitud_bot.salir(conv)
        return Respuesta(textos.menu(), "menu")
    if solicitud_bot.activo(conv):
        # Dentro del asistente de solicitud los números son opciones del paso, no del menú
        if usuario and not (config().modo_piloto and not usuario.piloto):
            p = solicitud_bot.continuar(s, usuario, conv, cuerpo)
            return Respuesta(p.texto, p.intencion)
        solicitud_bot.salir(conv)
    if t == "1":
        return Respuesta(textos.QUE_ES, "que_es")
    if t == "5":
        return _contenidos(s, usuario, conv, cuerpo, todos=True)

    # A partir de aquí, servicios solo para números registrados (información general sí se da)
    m = RE_CODIGO.search(cuerpo)
    pide_persona = t == "6" or any(p in t for p in PIDE_PERSONA)
    pide_puntos = t == "7" or t in {"puntos", "mis puntos"}
    if not usuario or (config().modo_piloto and not usuario.piloto):
        # RN-08: no registrado o fuera del piloto -> solo información general
        aviso = textos.registro() if not usuario else textos.NO_PILOTO
        if t in {"2", "3", "4"} or m or pide_persona or pide_puntos or conv.estado:
            return Respuesta(aviso, "registro" if not usuario else "no_piloto")
        info = _contenidos(s, None, conv, cuerpo)
        return info if info.entendido else Respuesta(aviso, "registro" if not usuario else "no_piloto")

    if pide_puntos:
        from ..solicitudes import puntos_de
        return Respuesta(textos.puntos(puntos_de(s, usuario.id)), "puntos")

    if t == "2" or t in {"solicitar", "nueva solicitud", "pedir recoleccion", "recoleccion"}:
        p = solicitud_bot.iniciar(s, usuario, conv)
        return Respuesta(p.texto, p.intencion)
    if t == "3":
        conv.estado = "esperando_residuo"
        return Respuesta(textos.PEDIR_RESIDUO, "pedir_residuo")
    if t == "4":
        return Respuesta(textos.PEDIR_CODIGO, "pedir_codigo")
    if m:
        return _estado(s, usuario, f"{m.group(1).upper()}-{int(m.group(2)):04d}")
    if pide_persona:
        return _derivar(s, usuario, conv, "pidio_persona", cuerpo)

    # Ayuda con el tipo de residuo: solo cuando la persona tiene la duda
    tiene_duda = conv.estado == "esperando_residuo" or any(d in t for d in DUDA)
    if tiene_duda or cascada.por_reglas(cuerpo):
        return _clasificar_texto(cuerpo, conv)

    info = _contenidos(s, usuario, conv, cuerpo)
    if info.entendido:
        return info
    return Respuesta(textos.NO_ENTIENDO, "no_entendido", entendido=False)


def _clasificar_texto(cuerpo: str, conv) -> Respuesta:
    try:
        sug = cascada.sugerir_texto(cuerpo)
    except IANoDisponible:
        return Respuesta(textos.CONTINGENCIA_IA.format(url=textos.enlace_formulario()), "ia_contingencia")
    conv.estado = None
    if sug.categoria == "desconocido":
        conv.estado = "esperando_residuo"
        return Respuesta("No logré identificarlo solo con el texto. 📷 Envíame una *foto* del residuo.",
                         "clasificar_pide_foto")
    if len(sug.flujos) == 1:
        conv.ultimo_flujo = sug.flujos[0]
    return Respuesta(textos.sugerencia(sug), f"clasificar_{sug.origen}")


# ---------------------------------------------------------------- imagen
def _imagen(s, imagen: dict, usuario, conv) -> Respuesta:
    if not usuario:
        return Respuesta(textos.registro(), "registro")
    if config().modo_piloto and not usuario.piloto:
        return Respuesta(textos.NO_PILOTO, "no_piloto")
    try:
        datos = obtener_cliente().descargar_media(imagen.get("id", ""))
    except ErrorWhatsApp:
        return Respuesta(textos.CONTINGENCIA_FOTO, "foto_contingencia")
    if solicitud_bot.activo(conv):
        try:
            p = solicitud_bot.foto(s, usuario, conv, datos)
        finally:
            del datos
        if p:
            return Respuesta(p.texto, p.intencion)
        return Respuesta("Ahora mismo estamos creando tu solicitud. Responde con el número de una opción "
                         "o escribe *menú* para salir.", "sol_foto_fuera_de_paso")
    try:
        sug = cascada.sugerir_imagen(datos)  # la foto se limpia y no se guarda
    except ImagenInvalida:
        return Respuesta(textos.CONTINGENCIA_FOTO, "foto_invalida")
    except IANoDisponible:
        return Respuesta(textos.CONTINGENCIA_IA.format(url=textos.enlace_formulario()), "ia_contingencia")
    finally:
        del datos
    conv.estado = None
    if sug.categoria == "desconocido":
        return Respuesta(textos.FOTO_NO_CLARA, "clasificar_foto_no_clara")
    if len(sug.flujos) == 1:
        conv.ultimo_flujo = sug.flujos[0]
    return Respuesta(textos.sugerencia(sug), "clasificar_modelo_vision")


# ---------------------------------------------------------------- estado (RN-07)
def _estado(s, usuario, codigo: str) -> Respuesta:
    """RN-07: solo el número registrado dueño de la solicitud puede consultarla."""
    sol = s.scalar(select(Solicitud).where(Solicitud.codigo == codigo))
    if not sol or sol.usuario_id != usuario.id:
        # Mismo mensaje si no existe o si es ajena: no se revela que el código existe
        return Respuesta(textos.SOLICITUD_NO_ENCONTRADA, "estado_rechazado")
    return Respuesta(textos.estado_solicitud(sol), "estado")


# ---------------------------------------------------------------- contenidos
def _contenidos(s, usuario, conv, cuerpo: str, todos: bool = False) -> Respuesta:
    """Responde SOLO con lo que hay en la tabla `contenidos`."""
    filas = s.scalars(select(Contenido).where(Contenido.activo.is_(True)).order_by(Contenido.id)).all()
    if todos:
        if not filas:
            return _sin_contenido(s, usuario, conv, "(pidió horarios, rutas o tutorial)")
        lista = "\n".join(f"• {c.titulo}" for c in filas[:10])
        return Respuesta(f"Tengo información sobre:\n{lista}\n\nEscribe el tema que te interesa "
                         "(ej.: *horario*, *ruta*, *tutorial*).", "info_lista")
    t = f" {normalizar(cuerpo)} "
    tipos = {v for k, v in TIPOS_CONTENIDO.items() if f" {k} " in t}
    elegidos = []
    for c in filas:
        claves = [normalizar(k) for k in c.palabras_clave.split(",") if k.strip()]
        if c.tipo in tipos or any(f" {k} " in t for k in claves):
            elegidos.append(c)
    if elegidos:
        return Respuesta("\n\n".join(f"*{c.titulo}*\n{c.cuerpo}" for c in elegidos[:2]), "info")
    if tipos:  # preguntó por horarios/rutas/tutorial pero no hay contenido cargado
        return _sin_contenido(s, usuario, conv, cuerpo)
    return Respuesta("", "sin_coincidencia", entendido=False)


def _sin_contenido(s, usuario, conv, cuerpo):
    if not usuario:
        return Respuesta("No tengo esa información todavía. " + textos.registro(), "sin_contenido")
    _registrar_caso(s, usuario, conv, "sin_contenido", cuerpo)
    return Respuesta(textos.SIN_CONTENIDO, "sin_contenido")


# ---------------------------------------------------------------- derivación
def _flujo_de(s, usuario, conv) -> str:
    if conv.ultimo_flujo:
        return conv.ultimo_flujo
    if usuario:
        ultima = s.scalar(select(Solicitud.flujo).where(Solicitud.usuario_id == usuario.id)
                          .order_by(Solicitud.id.desc()).limit(1))
        if ultima:
            return ultima
    return "general"


def _registrar_caso(s, usuario, conv, motivo, cuerpo) -> str:
    flujo = _flujo_de(s, usuario, conv)
    s.add(CasoCoordinacion(flujo=flujo, usuario_id=usuario.id if usuario else None,
                           motivo=motivo, resumen=(cuerpo or "")[:300]))
    return flujo


def _derivar(s, usuario, conv, motivo, cuerpo) -> Respuesta:
    if not usuario:
        return Respuesta(textos.registro(), "registro")
    flujo = _registrar_caso(s, usuario, conv, motivo, cuerpo)
    conv.estado = None
    return Respuesta(textos.derivado(flujo), "derivar")

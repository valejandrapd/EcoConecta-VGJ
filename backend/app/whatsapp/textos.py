"""Textos del bot (español, breves)."""
from ..config import config

NOMBRE_FLUJO = {"organico": "orgánico", "reciclable": "reciclable", "general": "general"}


def menu() -> str:
    return (
        "♻️ *EcoConecta Villas de San Pablo*: aprende a separar y solicita la recolección de tus residuos.\n\n"
        "Responde con un número:\n"
        "1️⃣ ¿Qué es EcoConecta?\n"
        "2️⃣ Solicitar una recolección\n"
        "3️⃣ ¿Mi residuo es orgánico o reciclable?\n"
        "4️⃣ Consultar una solicitud (ej.: ORG-0042)\n"
        "5️⃣ Horarios, rutas y tutorial\n"
        "6️⃣ Hablar con una persona\n"
        "7️⃣ Mis puntos"
    )


QUE_ES = (
    "EcoConecta conecta a hogares y unidades productivas de Villas de San Pablo con los *recicladores*, "
    "que recogen tus orgánicos (para compostaje en la huerta comunitaria) y tus reciclables. "
    "Pides la recolección, la coordinación te asigna día, hora y persona, y ganas puntos al entregar.\n"
    "Escribe *menú* para ver las opciones."
)


NO_PILOTO = ("Tu número está registrado, pero aún no está habilitado en el piloto de EcoConecta. "
             "La coordinación te avisará cuando puedas solicitar recolecciones. "
             "Mientras tanto puedo darte información general: escribe *menú*.")


def puntos(total: int) -> str:
    return f"Tienes *{total} puntos* por tus entregas en EcoConecta. ¡Gracias por separar! ♻️"


def registro() -> str:
    return ("Este número no está registrado en EcoConecta. Regístrate aquí para solicitar "
            f"recolecciones y consultar tus solicitudes: {config().url_registro}\n"
            "Mientras tanto puedo darte información general: escribe *menú*.")


def enlace_formulario(flujo: str | None = None) -> str:
    url = config().url_formulario
    return f"{url}?flujo={flujo}" if flujo else url


def solicitar() -> str:
    """Enlace al asistente web (alternativa al asistente por WhatsApp de `solicitud_bot`)."""
    return ("También puedes solicitar la recolección en la web (toma 1 minuto):\n"
            f"{enlace_formulario()}")


PEDIR_RESIDUO = ("Cuéntame qué residuo tienes (ej.: _cáscaras de papa_, _botella de vidrio_) "
                 "o envíame una *foto* 📷.")
PEDIR_CODIGO = "Escríbeme el código de tu solicitud, por ejemplo *ORG-0042* o *REC-0017*."
NO_ENTIENDO = "No te entendí 🤔. Escribe *menú* para ver lo que puedo hacer."
SOLO_TEXTO_FOTO = "Por ahora entiendo *texto* y *fotos*. Escribe *menú* para ver las opciones."
CONTINGENCIA_IA = ("No pude analizar tu residuo en este momento. Intenta de nuevo en unos minutos "
                   "o solicita la recolección directamente: {url}")
CONTINGENCIA_FOTO = "No pude descargar tu foto. ¿Puedes enviarla otra vez?"
FOTO_NO_CLARA = "No logro distinguir el residuo en la foto. Toma otra más cerca y con buena luz 📷"
LIMITE = ("Alcanzaste el límite de mensajes de hoy. Mañana puedo seguir ayudándote, "
          "o usa la web: {url}")
SOLICITUD_NO_ENCONTRADA = ("No encontré una solicitud con ese código asociada a este número. "
                           "Revisa el código o escribe *6* para hablar con la coordinación.")
SIN_CONTENIDO = ("No tengo esa información en este momento. Le pasé tu pregunta a la coordinación "
                 "y te contactarán pronto.")


COORDINACION = {"organico": "La coordinación de huerta", "reciclable": "La coordinación de reciclaje",
                "general": "La coordinación de EcoConecta"}


def derivado(flujo: str) -> str:
    return f"Listo 🙌. {COORDINACION.get(flujo, COORDINACION['general'])} te contactará pronto por este medio."


CONSEJO = {
    "organico": "Va en la caneca de *orgánicos* (restos de comida, cáscaras, hojas).",
    "reciclable": "Va en la caneca de *reciclables*. Entrégalo limpio y seco.",
}
NOMBRE_CATEGORIA = {"organico": "Orgánico 🟢", "reciclable": "Reciclable 🔵"}


def sugerencia(s) -> str:
    """Texto para una `Sugerencia` de la cascada de IA."""
    objeto = f" ({s.objeto})" if s.objeto else ""
    pie = "\n_Es una sugerencia automática: la coordinación confirma al recibir tu solicitud._"
    if s.categoria in ("organico", "reciclable"):
        return (f"Sugerencia{objeto}: *{NOMBRE_CATEGORIA[s.categoria]}* (confianza {s.confianza}).\n"
                f"{CONSEJO[s.categoria]}\n"
                f"Para solicitar la recolección escribe *2* y te guío paso a paso, "
                f"o usa la web: {enlace_formulario(s.categoria)}{pie}")
    if s.categoria == "mezcla":
        return (f"Veo una *mezcla* de orgánico y reciclable{objeto} (confianza {s.confianza}).\n"
                "Sepáralos y haz *dos solicitudes*:\n"
                f"🟢 Orgánico: {enlace_formulario('organico')}\n"
                f"🔵 Reciclable: {enlace_formulario('reciclable')}{pie}")
    if s.categoria == "no_aprovechable":
        return (f"Esto{objeto} no parece orgánico ni reciclable (confianza {s.confianza}). "
                "Va con los residuos ordinarios; EcoConecta no lo recoge.")
    return ""


ESTADOS = {"recibida": "Recibida", "en_revision": "En revisión por la coordinación",
           "asignada": "Asignada (pendiente de fecha y hora)", "programada": "Programada",
           "recolectada": "Recolectada ✅", "cancelada": "Cancelada"}


def estado_solicitud(sol) -> str:
    lineas = [f"Solicitud *{sol.codigo}* ({NOMBRE_FLUJO.get(sol.flujo, sol.flujo)})",
              f"Estado: {ESTADOS.get(sol.estado, sol.estado)}"]
    if sol.estado == "programada":
        if sol.fecha_programada:
            lineas.append(f"Fecha: {sol.fecha_programada:%d/%m/%Y}")
        if sol.hora_programada:
            lineas.append(f"Hora: {sol.hora_programada:%H:%M}")
        if sol.reciclador:
            lineas.append(f"Persona encargada: {sol.reciclador.nombre}")
    if sol.estado == "recolectada" and sol.recoleccion:
        lineas.append(f"Puntos ganados: {sol.recoleccion.puntos}")
    return "\n".join(lineas)

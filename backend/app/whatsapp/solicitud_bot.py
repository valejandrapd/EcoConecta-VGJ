"""Asistente de nueva solicitud por WhatsApp con menú numérico.

Sigue los mismos pasos que el asistente web (`frontend/app/solicitudes/nueva`):
tipo -> consejos -> tamaño -> días -> horario -> dirección -> puntos -> resumen.
El paso actual va en `ConversacionWhatsapp.estado` ("sol_<paso>") y las respuestas en
`ConversacionWhatsapp.borrador` (JSON), que se borra al crear o cancelar la solicitud.
"""
import json
import re
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from ..ia import cascada
from ..ia.imagen import ImagenInvalida
from ..ia.modelo import IANoDisponible
from ..ia.reglas import normalizar
from ..models import DIAS_SEMANA, DireccionUsuario


def _reglas():
    # Import diferido: solicitudes -> notificaciones -> whatsapp crearía un ciclo al cargar el bot
    from .. import solicitudes
    return solicitudes

PREFIJO = "sol_"
VENCE = timedelta(hours=6)  # un borrador abandonado se descarta
PIE = "\n\n_Escribe *atrás* para volver o *menú* para salir._"
NUM = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

NOMBRE_FLUJO = {"organico": "Orgánico 🟢", "reciclable": "Reciclable 🔵"}
NOMBRE_TAMANO = {"pequeno": "Pequeño", "mediano": "Mediano", "grande": "Grande"}
DETALLE_TAMANO = {
    "organico": {"pequeno": "un par de cáscaras y hojas", "mediano": "una bolsita de cáscaras",
                 "grande": "una bolsa llena o más"},
    "reciclable": {"pequeno": "una botella o una lata", "mediano": "una bolsita de envases",
                   "grande": "una bolsa llena y cajas"},
}
NOMBRE_DIA = {"lun": "Lun", "mar": "Mar", "mie": "Mié", "jue": "Jue", "vie": "Vie", "sab": "Sáb", "dom": "Dom"}
DIA_ESCRITO = {"lun": ("lunes", "lun"), "mar": ("martes", "mar"), "mie": ("miercoles", "mie"),
               "jue": ("jueves", "jue"), "vie": ("viernes", "vie"), "sab": ("sabado", "sab"),
               "dom": ("domingo", "dom")}
FRANJAS = [("Mañana", 7, 12), ("Tarde", 12, 17), ("Todo el día", 7, 17)]
HORA_MIN, HORA_MAX = 6, 19
ETIQUETAS = ["Casa mamá", "Trabajo", "Mi negocio", "Casa familiar"]
BONIFICACION = {"1": "tiendas", "2": "huerto"}
NOMBRE_BONIFICACION = {"tiendas": "Canje en tiendas de la zona", "huerto": "Servicios del huerto"}
SI = {"1", "si", "ok", "listo", "entendido", "dale", "de acuerdo", "vale"}

CONSEJOS = {
    "organico": ("*Antes de entregarlo* 🍌\n"
                 "• *Sin etiquetas:* quita los adhesivos de las frutas y las etiquetas de los empaques.\n"
                 "• Solo restos de comida, cáscaras y hojas. Sin bolsas plásticas."),
    "reciclable": ("*Antes de entregarlo* ♻️\n"
                   "• *Cartón y papel secos:* que no estén mojados ni con grasa (una caja de pizza con aceite no se recicla).\n"
                   "• *Botellas y envases limpios:* enjuágalos, déjalos escurrir y aplasta las botellas.\n\n"
                   "*¿Qué plástico es?* Busca el número dentro del triángulo de flechas:\n"
                   "✅ 1 PET (botellas de agua, gaseosa y aceite)\n"
                   "✅ 2 PEAD (tarros de leche, champú y detergente)\n"
                   "❌ 3 PVC (tubos, mangueras, blísteres)\n"
                   "⚠️ 4 PEBD (bolsas y plástico de envolver: solo limpias y secas)\n"
                   "✅ 5 PP (tapas, tarros de margarina, vasos de yogur)\n"
                   "❌ 6 PS (icopor, vasos y platos desechables)\n"
                   "❌ 7 Otros (mezclas)"),
}


class Paso:
    """Respuesta de un paso: texto a enviar e intención para el registro de mensajes."""
    def __init__(self, texto: str, intencion: str):
        self.texto, self.intencion = texto, intencion


# ------------------------------------------------------------------ estado
def activo(conv) -> bool:
    return bool(conv.estado and conv.estado.startswith(PREFIJO))


def _borrador(conv) -> dict:
    try:
        b = json.loads(conv.borrador or "{}")
    except ValueError:
        b = {}
    return b


def _guardar(conv, b: dict, paso: str):
    historial = b.setdefault("historial", [])
    actual = conv.estado[len(PREFIJO):] if activo(conv) else None
    if actual and actual != paso and (not historial or historial[-1] != actual):
        historial.append(actual)
    conv.estado = PREFIJO + paso
    conv.borrador = json.dumps(b, ensure_ascii=False)
    conv.borrador_en = datetime.now(timezone.utc)


def salir(conv):
    if activo(conv):
        conv.estado = None
    conv.borrador = None
    conv.borrador_en = None


def vencido(conv) -> bool:
    en = conv.borrador_en
    if not en:
        return False
    if en.tzinfo is None:
        en = en.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - en > VENCE


# ------------------------------------------------------------------ entrada
def iniciar(s, usuario, conv, flujo: str | None = None) -> Paso:
    conv.estado, conv.borrador = None, None
    b = {}
    if flujo in NOMBRE_FLUJO:
        b["flujo"] = flujo
        return _ir(s, usuario, conv, b, "consejos")
    return _ir(s, usuario, conv, b, "tipo")


def continuar(s, usuario, conv, cuerpo: str) -> Paso:
    """Atiende un texto mientras la persona está dentro del asistente."""
    if vencido(conv):
        salir(conv)
        return Paso("Tu solicitud anterior quedó sin terminar y la descarté. Empecemos de nuevo.\n\n"
                    + iniciar(s, usuario, conv).texto, "sol_vencida")
    b = _borrador(conv)
    paso = conv.estado[len(PREFIJO):]
    t = normalizar(cuerpo)
    if t in {"atras", "volver", "regresar"}:
        historial = b.get("historial", [])
        anterior = historial.pop() if historial else "tipo"
        conv.estado = None  # para que _guardar no apile el paso del que salimos
        return _ir(s, usuario, conv, b, anterior)
    manejador = MANEJADORES.get(paso)
    if not manejador:
        salir(conv)
        return iniciar(s, usuario, conv)
    return manejador(s, usuario, conv, b, cuerpo, t)


def foto(s, usuario, conv, datos: bytes) -> Paso | None:
    """Foto recibida durante el asistente: solo se usa en el paso "No estoy seguro"."""
    if conv.estado != PREFIJO + "duda":
        return None
    try:
        sug = cascada.sugerir_imagen(datos)
    except ImagenInvalida:
        return Paso("No pude leer la foto. Envíala otra vez o escríbeme qué es." + PIE, "sol_duda")
    except IANoDisponible:
        return _ir(s, usuario, conv, _borrador(conv), "tipo",
                   antes="No pude analizar la foto en este momento. Elige el tipo tú mismo:")
    return _resultado_duda(s, usuario, conv, _borrador(conv), sug)


# ------------------------------------------------------------------ pasos
def _ir(s, usuario, conv, b, paso, antes: str = "") -> Paso:
    texto = PREGUNTAS[paso](s, usuario, b)
    _guardar(conv, b, paso)
    return Paso((antes + "\n\n" if antes else "") + texto, f"sol_{paso}")


def _otra_vez(s, usuario, conv, b, paso, aviso="No te entendí. Responde con el número de una opción.") -> Paso:
    return Paso(f"🤔 {aviso}\n\n" + PREGUNTAS[paso](s, usuario, b), f"sol_{paso}_repetir")


def _numeros(t: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", t)]


def _opcion(t: str, maximo: int) -> int | None:
    n = _numeros(t)
    return n[0] if len(n) == 1 and 1 <= n[0] <= maximo and t.strip().isdigit() else None


def _encabezado(n: int) -> str:
    return f"🧾 *Nueva solicitud* · paso {n} de 8\n"


# tipo ------------------------------------------------------------------
def _p_tipo(s, usuario, b):
    return (_encabezado(1) + "*¿Qué vas a entregar?*\n"
            f"{NUM[1]} 🟢 *Orgánicos*: cáscaras, restos de comida y hojas. Van a la huerta comunitaria.\n"
            f"{NUM[2]} 🔵 *Reciclables*: plástico, vidrio, metal, papel y cartón limpios.\n"
            f"{NUM[3]} 🤔 *No estoy seguro*: te ayudo a saberlo." + PIE)


def _r_tipo(s, usuario, conv, b, cuerpo, t):
    if t in {"1", "organico", "organicos"}:
        b["flujo"] = "organico"
    elif t in {"2", "reciclable", "reciclables"}:
        b["flujo"] = "reciclable"
    elif t in {"3", "no se", "no estoy seguro"}:
        return _ir(s, usuario, conv, b, "duda")
    else:
        return _otra_vez(s, usuario, conv, b, "tipo")
    return _ir(s, usuario, conv, b, "consejos")


# duda ------------------------------------------------------------------
def _p_duda(s, usuario, b):
    return ("Cuéntame qué vas a entregar (ej.: _cáscaras de banano_, _botella de vidrio_) "
            "o envíame una *foto* 📷 y te digo si es orgánico o reciclable." + PIE)


def _r_duda(s, usuario, conv, b, cuerpo, t):
    if t in {"1", "2"}:  # cambió de opinión y eligió el tipo
        return _r_tipo(s, usuario, conv, b, cuerpo, t)
    try:
        sug = cascada.sugerir_texto(cuerpo)
    except IANoDisponible:
        return _ir(s, usuario, conv, b, "tipo", antes="No pude analizarlo en este momento. Elige el tipo tú mismo:")
    return _resultado_duda(s, usuario, conv, b, sug)


def _resultado_duda(s, usuario, conv, b, sug) -> Paso:
    objeto = f" ({sug.objeto})" if sug.objeto else ""
    nota = "\n_Es una ayuda automática: tú eliges y la coordinación confirma._"
    if sug.categoria in NOMBRE_FLUJO:
        b["flujo"] = sug.categoria
        conv.ultimo_flujo = sug.categoria
        return _ir(s, usuario, conv, b, "consejos",
                   antes=f"Tu residuo{objeto} es *{NOMBRE_FLUJO[sug.categoria].upper()}* (confianza {sug.confianza}).{nota}")
    if sug.categoria == "mezcla":
        return _ir(s, usuario, conv, b, "tipo",
                   antes=f"Veo una *mezcla*{objeto}. Sepáralos y haz una solicitud por cada tipo. ¿Con cuál empezamos?")
    if sug.categoria == "no_aprovechable":
        return _ir(s, usuario, conv, b, "tipo",
                   antes=f"Esto{objeto} no parece orgánico ni reciclable: va con los residuos ordinarios y "
                         "EcoConecta no lo recoge. Si tienes otra cosa, elige el tipo:")
    return Paso("No logré identificarlo. Envíame una *foto* 📷 o elige: *1* orgánicos, *2* reciclables." + PIE,
                "sol_duda_repetir")


# consejos --------------------------------------------------------------
def _p_consejos(s, usuario, b):
    return _encabezado(2) + CONSEJOS[b["flujo"]] + f"\n\n{NUM[1]} ¡Entendido!" + PIE


def _r_consejos(s, usuario, conv, b, cuerpo, t):
    if t in SI:
        return _ir(s, usuario, conv, b, "tamano")
    return _otra_vez(s, usuario, conv, b, "consejos", "Responde *1* cuando estés listo.")


# tamaño ----------------------------------------------------------------
def _p_tamano(s, usuario, b):
    d = DETALLE_TAMANO[b["flujo"]]
    return (_encabezado(3) + "*¿Qué tanto tienes?*\n"
            + "\n".join(f"{NUM[i]} *{NOMBRE_TAMANO[k]}*: {d[k]}" for i, k in enumerate(d, 1)) + PIE)


def _r_tamano(s, usuario, conv, b, cuerpo, t):
    claves = list(NOMBRE_TAMANO)
    n = _opcion(t, 3)
    elegido = claves[n - 1] if n else next((k for k in claves if normalizar(NOMBRE_TAMANO[k]) == t), None)
    if not elegido:
        return _otra_vez(s, usuario, conv, b, "tamano")
    b["tamano"] = elegido
    return _ir(s, usuario, conv, b, "dias")


# días ------------------------------------------------------------------
def _proxima(indice: int) -> date:
    hoy = date.today()
    return hoy + timedelta(days=(indice - hoy.weekday()) % 7 or 7)


def _p_dias(s, usuario, b):
    lineas = [f"{NUM[i + 1]} {NOMBRE_DIA[d]} {_proxima(i):%d}" for i, d in enumerate(DIAS_SEMANA)]
    return (_encabezado(4) + "*¿Qué días puedes entregarlo?* Marca todos los días en que alguien estará.\n"
            + "\n".join(lineas)
            + f"\n{NUM[8]} Entre semana (lun a vie)\n{NUM[9]} Fin de semana\n{NUM[10]} Todos los días\n\n"
              "Puedes elegir varios separados por coma, por ejemplo: *2, 4*" + PIE)


def _r_dias(s, usuario, conv, b, cuerpo, t):
    dias = set()
    for n in _numeros(t):
        if 1 <= n <= 7:
            dias.add(DIAS_SEMANA[n - 1])
        elif n == 8:
            dias.update(DIAS_SEMANA[:5])
        elif n == 9:
            dias.update(DIAS_SEMANA[5:])
        elif n == 10:
            dias.update(DIAS_SEMANA)
        else:
            return _otra_vez(s, usuario, conv, b, "dias", f"No hay opción {n}. Usa números del 1 al 10.")
    palabras = set(t.split())
    for d, nombres in DIA_ESCRITO.items():
        if palabras & set(nombres):
            dias.add(d)
    if not dias:
        return _otra_vez(s, usuario, conv, b, "dias", "Elige al menos un día.")
    b["dias"] = [d for d in DIAS_SEMANA if d in dias]
    return _ir(s, usuario, conv, b, "horario",
               antes="📅 Días: *" + ", ".join(NOMBRE_DIA[d] for d in b["dias"]) + "*")


# horario ---------------------------------------------------------------
def hora12(h: int) -> str:
    if h == 12:
        return "12 m."
    return f"{h % 12 or 12} {'a. m.' if h < 12 else 'p. m.'}"


def _p_horario(s, usuario, b):
    lineas = [f"{NUM[i]} *{n}*: {hora12(d)} a {hora12(h)}" for i, (n, d, h) in enumerate(FRANJAS, 1)]
    return (_encabezado(5) + "*¿A qué hora estás disponible?*\n" + "\n".join(lineas)
            + f"\n{NUM[4]} *Otro horario*: tú lo eliges" + PIE)


def _r_horario(s, usuario, conv, b, cuerpo, t):
    n = _opcion(t, 4)
    if n in (1, 2, 3):
        _, b["desde"], b["hasta"] = FRANJAS[n - 1]
        return _ir(s, usuario, conv, b, "direccion")
    if n == 4:
        return _ir(s, usuario, conv, b, "horario_propio")
    return _otra_vez(s, usuario, conv, b, "horario")


def _p_horario_propio(s, usuario, b):
    return ("Escribe desde qué hora y hasta qué hora, entre las 6 a. m. y las 7 p. m.\n"
            "Por ejemplo: *8 a 11* o *2 pm a 5 pm*." + PIE)


def _hora(numero: int, sufijo: str) -> int:
    if sufijo.startswith("p") and numero < 12:
        return numero + 12
    if sufijo.startswith("a") and numero == 12:
        return 0
    return numero


def _r_horario_propio(s, usuario, conv, b, cuerpo, t):
    partes = re.findall(r"(\d{1,2})(?:\s*(am|pm|a m|p m|m))?", t)
    horas = [_hora(int(n), suf.replace(" ", "")) for n, suf in partes]
    # "2 a 5 pm": si solo la última trae p. m., aplícala también a la primera
    if len(partes) == 2 and partes[1][1].startswith("p") and not partes[0][1] and horas[0] < 12 and horas[0] + 12 < horas[1]:
        horas[0] += 12
    if len(horas) != 2:
        return _otra_vez(s, usuario, conv, b, "horario_propio", "Necesito dos horas: desde y hasta.")
    desde, hasta = horas
    if not (HORA_MIN <= desde < hasta <= HORA_MAX):
        return _otra_vez(s, usuario, conv, b, "horario_propio",
                         "La hora de inicio debe ser antes que la de fin, entre 6 a. m. y 7 p. m.")
    b["desde"], b["hasta"] = desde, hasta
    return _ir(s, usuario, conv, b, "direccion")


# dirección -------------------------------------------------------------
def _guardadas(s, usuario):
    return s.scalars(select(DireccionUsuario).where(DireccionUsuario.usuario_id == usuario.id)
                     .order_by(DireccionUsuario.etiqueta)).all()


def _p_direccion(s, usuario, b):
    lineas = [_encabezado(6) + "*¿Estarás en esta dirección?*"]
    if usuario.direccion:
        zona = f" ({usuario.zona})" if usuario.zona else ""
        lineas.append(f"📍 {usuario.direccion}{zona}\n")
        lineas.append(f"{NUM[1]} Sí, aquí\n{NUM[2]} No, en otra dirección")
    else:
        lineas.append(f"{NUM[2]} Escribir la dirección de recolección")
    for i, d in enumerate(_guardadas(s, usuario)[:7], 3):
        zona = f" ({d.zona})" if d.zona else ""
        lineas.append(f"{NUM[i]} 🏷️ {d.etiqueta}: {d.direccion}{zona}")
    return "\n".join(lineas) + PIE


def _r_direccion(s, usuario, conv, b, cuerpo, t):
    guardadas = _guardadas(s, usuario)[:7]
    n = _opcion(t, 2 + len(guardadas))
    if n == 1 and usuario.direccion or t in {"si", "si aqui", "aqui"} and usuario.direccion:
        b.update(direccion=None, etiqueta=None, zona=usuario.zona)
        if not usuario.zona:
            b["zona_para"] = "principal"
            return _ir(s, usuario, conv, b, "dir_zona")
        return _ir(s, usuario, conv, b, "bonificacion")
    if n == 2 or t in {"no", "otra"}:
        return _ir(s, usuario, conv, b, "dir_nueva")
    if n and n >= 3:
        d = guardadas[n - 3]
        b.update(direccion=d.direccion, etiqueta=d.etiqueta, zona=d.zona)
        if not d.zona:
            b["zona_para"] = "guardada"
            return _ir(s, usuario, conv, b, "dir_zona")
        return _ir(s, usuario, conv, b, "bonificacion")
    return _otra_vez(s, usuario, conv, b, "direccion")


def _p_dir_nueva(s, usuario, b):
    return "Escribe la *dirección de recolección* (ej.: _Manzana 7, casa 3_)." + PIE


def _r_dir_nueva(s, usuario, conv, b, cuerpo, t):
    direccion = " ".join((cuerpo or "").split())[:255]
    if len(direccion) < 3 or t.isdigit():
        return _otra_vez(s, usuario, conv, b, "dir_nueva", "Escribe la dirección completa.")
    b.update(direccion=direccion, etiqueta=None, zona=None, zona_para="nueva")
    return _ir(s, usuario, conv, b, "dir_zona")


def _p_dir_zona(s, usuario, b):
    zonas = _reglas().zonas_activas(s)
    return ("*¿En qué zona queda?* Así llega el reciclador correcto.\n"
            + "\n".join(f"{NUM[i] if i < len(NUM) else str(i) + '.'} {z}" for i, z in enumerate(zonas, 1)) + PIE)


def _r_dir_zona(s, usuario, conv, b, cuerpo, t):
    zonas = _reglas().zonas_activas(s)
    n = _opcion(t, len(zonas))
    zona = zonas[n - 1] if n else next((z for z in zonas if normalizar(z) == t), None)
    if not zona:
        return _otra_vez(s, usuario, conv, b, "dir_zona")
    b["zona"] = zona
    if b.get("zona_para") == "nueva":
        return _ir(s, usuario, conv, b, "dir_etiqueta")
    return _ir(s, usuario, conv, b, "bonificacion")


def _p_dir_etiqueta(s, usuario, b):
    opciones = "\n".join(f"{NUM[i]} {e}" for i, e in enumerate(ETIQUETAS, 1))
    return ("*Ponle un nombre* para guardarla y elegirla más rápido la próxima vez:\n" + opciones
            + f"\n{NUM[5]} No guardarla\n\nO escribe otro nombre." + PIE)


def _r_dir_etiqueta(s, usuario, conv, b, cuerpo, t):
    n = _opcion(t, 5)
    if n and n <= 4:
        b["etiqueta"] = ETIQUETAS[n - 1]
    elif n == 5 or t in {"no", "no guardarla"}:
        b["etiqueta"] = None
    else:
        nombre = " ".join((cuerpo or "").split())[:40]
        if len(nombre) < 2 or t.isdigit():
            return _otra_vez(s, usuario, conv, b, "dir_etiqueta")
        b["etiqueta"] = nombre
    return _ir(s, usuario, conv, b, "bonificacion")


# bonificación ----------------------------------------------------------
def _p_bonificacion(s, usuario, b):
    return (_encabezado(7) + "*¿Cómo quieres tus puntos?* Cuando se recoja tu solicitud, harán crecer la insignia que elijas.\n"
            f"{NUM[1]} 🐷 *Tiendas de la zona*: puntos de canje. Tu alcancía crece cada 10 puntos.\n"
            f"{NUM[2]} 🌺 *Servicios del huerto*: tu trinitaria crece cada 5 puntos hasta florecer." + PIE)


def _r_bonificacion(s, usuario, conv, b, cuerpo, t):
    elegido = BONIFICACION.get(t) or ("tiendas" if "tienda" in t else "huerto" if "huerto" in t else None)
    if not elegido:
        return _otra_vez(s, usuario, conv, b, "bonificacion")
    b["bonificacion"] = elegido
    return _ir(s, usuario, conv, b, "resumen")


# resumen ---------------------------------------------------------------
def _p_resumen(s, usuario, b):
    direccion = b.get("direccion") or usuario.direccion
    etiqueta = f"🏷️ {b['etiqueta']}: " if b.get("etiqueta") else ""
    zona = f" · {b['zona']}" if b.get("zona") else ""
    nota = f"\n📝 *Nota:* {b['nota']}" if b.get("nota") else ""
    return (_encabezado(8) + "*Revisa y confirma*\n"
            f"♻️ *Residuo:* {NOMBRE_FLUJO[b['flujo']]} · {NOMBRE_TAMANO[b['tamano']]}\n"
            f"📅 *Días:* {', '.join(NOMBRE_DIA[d] for d in b['dias'])}\n"
            f"🕒 *Horario:* {hora12(b['desde'])} a {hora12(b['hasta'])}\n"
            f"📍 *Dirección:* {etiqueta}{direccion}{zona}\n"
            f"⭐ *Puntos:* {NOMBRE_BONIFICACION[b['bonificacion']]}{nota}\n\n"
            f"{NUM[1]} ✅ Crear solicitud\n{NUM[2]} 📝 {'Cambiar la' if b.get('nota') else 'Agregar una'} nota para el reciclador\n"
            f"{NUM[3]} ❌ Cancelar" + PIE)


def _r_resumen(s, usuario, conv, b, cuerpo, t):
    if t in {"1", "crear", "si", "confirmar"}:
        return _crear(s, usuario, conv, b)
    if t in {"2", "nota"}:
        return _ir(s, usuario, conv, b, "nota")
    if t in {"3", "cancelar", "no"}:
        salir(conv)
        return Paso("Listo, no creé la solicitud. Escribe *2* cuando quieras empezar otra o *menú* para ver las opciones.",
                    "sol_cancelada")
    return _otra_vez(s, usuario, conv, b, "resumen")


def _p_nota(s, usuario, b):
    return "Escribe la nota (ej.: _timbre dañado, llamar al llegar_)." + PIE


def _r_nota(s, usuario, conv, b, cuerpo, t):
    nota = " ".join((cuerpo or "").split())[:300]
    if not nota:
        return _otra_vez(s, usuario, conv, b, "nota", "La nota está vacía.")
    b["nota"] = nota
    # Vuelve al resumen sin apilar la nota ni repetir el resumen en el historial
    conv.estado = None
    historial = b.get("historial", [])
    if historial and historial[-1] == "resumen":
        historial.pop()
    return _ir(s, usuario, conv, b, "resumen")


def _crear(s, usuario, conv, b) -> Paso:
    reglas = _reglas()
    try:
        sol = reglas.crear(
            s, usuario, b["flujo"], tamano=b["tamano"], dias=b["dias"],
            hora_desde=time(b["desde"]), hora_hasta=time(b["hasta"]), bonificacion=b["bonificacion"],
            direccion=b.get("direccion"), direccion_etiqueta=b.get("etiqueta"), zona=b.get("zona"),
            observaciones=b.get("nota") or "", avisar_usuario=False)
    except (reglas.ErrorSolicitud, reglas.SinPermiso) as e:
        return Paso(f"No pude crear la solicitud: {e}. Revisa los datos o escribe *6* para hablar con una persona.",
                    "sol_error")
    salir(conv)
    conv.ultimo_flujo = sol.flujo
    return Paso(f"🎉 *¡Solicitud creada!*\nTu código es *{sol.codigo}*.\n\n"
                "La coordinación la revisará y te avisaremos por aquí el día, la hora y quién la recogerá. "
                "Para consultarla, escribe el código.\n\nEscribe *menú* para volver al inicio.", "sol_creada")


PREGUNTAS = {
    "tipo": _p_tipo, "duda": _p_duda, "consejos": _p_consejos, "tamano": _p_tamano, "dias": _p_dias,
    "horario": _p_horario, "horario_propio": _p_horario_propio, "direccion": _p_direccion,
    "dir_nueva": _p_dir_nueva, "dir_zona": _p_dir_zona, "dir_etiqueta": _p_dir_etiqueta,
    "bonificacion": _p_bonificacion, "resumen": _p_resumen, "nota": _p_nota,
}
MANEJADORES = {
    "tipo": _r_tipo, "duda": _r_duda, "consejos": _r_consejos, "tamano": _r_tamano, "dias": _r_dias,
    "horario": _r_horario, "horario_propio": _r_horario_propio, "direccion": _r_direccion,
    "dir_nueva": _r_dir_nueva, "dir_zona": _r_dir_zona, "dir_etiqueta": _r_dir_etiqueta,
    "bonificacion": _r_bonificacion, "resumen": _r_resumen, "nota": _r_nota,
}

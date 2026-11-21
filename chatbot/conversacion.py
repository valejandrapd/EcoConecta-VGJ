"""Conversación de WhatsApp: guía a la persona paso a paso y registra la solicitud completa.

atender(contacto, texto, foto, clasificar_foto, segmentar_foto, origen) -> lista de mensajes a enviar. No envía nada ni conoce Whapi.

Pasos: MENU -> GENERADOR -> RESIDUO (-> FOTO) (-> ITEM_DUDA) -> CONFIRMAR_TIPO (-> TIPO_MANUAL) -> DIRECCION
       -> DISPONIBILIDAD -> OBSERVACIONES -> CONFIRMAR -> (solicitud creada)
Si la persona nombra varios residuos de distinto tipo (texto, audio o foto), se crea UNA solicitud por tipo
(cada tipo lo recoge un colectivo distinto) con la misma dirección y disponibilidad.
La IA solo SUGIERE el tipo de residuo; la persona lo confirma. La asignación, la programación y el cierre
los hace el colectivo (coordinador / recolector), nunca el bot.
"""
import logging
import os
import re

import backend
import contenido
import core
import db
from clasificador import normalizar

log = logging.getLogger("ecoconecta")

MENU = ("♻️ *EcoConecta* · Villas de San Pablo\n¿Qué quieres hacer?\n"
        "*1* Solicitar recolección\n*2* Consultar mis solicitudes\n*3* Ver mis puntos\n"
        "*4* Aprender a separar\n*5* ¿Qué residuo es?\n"
        "Responde con el número. Escribe *menú* cuando quieras volver aquí.")
NO_HABILITADO = ("Hola 👋 Por ahora EcoConecta está en *piloto* y tu número aún no está habilitado. "
                 "Cuando lo esté, podrás pedir recolecciones por aquí.")
SOLO_TEXTO_FOTO = "Por ahora entiendo *texto*, *audios* 🎙️ y *fotos* 📷 🙂"
CATS = ("ORGANICO", "RECICLABLE")
NOMBRE_TIPO = {"ORGANICO": "🟢 *ORGÁNICO*", "RECICLABLE": "🔵 *RECICLABLE*"}
OTRO_TXT_CORTO = "⚫ _{}_ no se recoge: va en la caneca de ordinarios."
OTRO_TXT = ("⚫ Eso parece *no aprovechable* (ni orgánico ni reciclable): va en la caneca de residuos ordinarios, "
            "por eso no genera una recolección.")
ESTADOS_TXT = {"recibida": "Recibida", "en_revision": "En revisión", "asignada": "Asignada",
               "programada": "Programada", "recolectada": "Recolectada", "cancelada": "Cancelada"}
NUMEROS = {"1": 1, "uno": 1, "2": 2, "dos": 2, "3": 3, "tres": 3, "4": 4, "cuatro": 4, "5": 5, "cinco": 5}
SI = {"si", "s", "1", "claro", "ok", "correcto", "confirmo", "confirmar", "dale"}
NO = {"no", "n", "2", "incorrecto"}
SALIDAS = {"menu", "inicio", "hola", "ayuda", "buenas", "hi", "cancelar", "salir", "volver"}


def habilitado(contacto):
    """RN-08: si PILOTO_NUMEROS tiene números (separados por coma), solo ellos pueden usar el bot."""
    lista = [re.sub(r"\D", "", n) for n in os.environ.get("PILOTO_NUMEROS", "").split(",") if n.strip()]
    return not lista or re.sub(r"\D", "", contacto) in lista


def _ahora_tipo(cat):
    return {"ORGANICO": "huerteros", "RECICLABLE": "recicladores"}[cat]


def _linea(s):
    extra = ""
    p = s.get("programacion")
    if s["estado"] == "programada" and p:
        extra = f" · {p['dia']} {p['hora']} con {p['recolector']}"
    elif s["estado"] == "asignada" and s.get("recolector"):
        extra = f" · {s['recolector']}"
    elif s["estado"] == "recolectada":
        extra = f" · +{s['puntos']} puntos"
    return f"*{s['codigo']}* · {s['flujo']} · {ESTADOS_TXT.get(s['estado'], s['estado'])}{extra}"


def _consultar(contacto, t, texto):
    m = re.search(r"res-\d{8}-\d+", (texto or "").lower())
    if m:
        try:
            s = backend.consultar(m.group(0).upper(), contacto)
        except core.SolicitudNoEncontrada:
            return ["No encontré esa solicitud en tu cuenta. Revisa el código (ej.: RES-20261120-0001)."]
        return [_linea(s)]
    lista = backend.listar(contacto, 3)
    if not lista:
        return ["Aún no tienes solicitudes. Escribe *1* para pedir una recolección."]
    return ["Tus últimas solicitudes:\n" + "\n".join(_linea(s) for s in lista)
            + "\nPara ver una: *estado RES-AAAAMMDD-NNNN*"]


def _foto_a_segmentos(clasificar_foto, segmentar_foto):
    """La foto se segmenta con `segmentar_foto`; si solo hay un clasificador de un residuo, se adapta."""
    return segmentar_foto or clasificar_foto


def _clasificar_entrada(texto, foto, clasificar_foto, segmentar_foto, origen):
    """-> (resultado_de_core.segmentar | None, mensaje_de_error | None)."""
    try:
        if foto is not None:
            datos, mime = foto()
            return core.segmentar(imagen=datos, mime=mime, segmentar_foto=_foto_a_segmentos(clasificar_foto, segmentar_foto)), None
        r = core.segmentar(texto=texto)
        if origen == "audio":
            r["metodo"] = "audio"
        return r, None
    except Exception:  # noqa: BLE001 - el usuario debe recibir una respuesta amable
        log.exception("Fallo al clasificar el residuo")
        return None, "No pude procesar eso en este momento. Intenta de nuevo, por favor."


def _tipo_manual(t):
    if t in {"1", "organico", "organicos"}:
        return "ORGANICO"
    if t in {"2", "reciclable", "reciclables"}:
        return "RECICLABLE"
    return None


def _lista_grupos(grupos):
    """Líneas '🟢 ORGÁNICO: cáscaras → huerteros' para un dict {categoria: objetos}."""
    return "\n".join(f"{NOMBRE_TIPO[c]}{': ' + o if o else ''} → *{_ahora_tipo(c)}*" for c, o in grupos.items())


def _a_texto(grupos):
    return {c: ", ".join(grupos[c]) for c in CATS if grupos.get(c)}


def _pedir_confirmacion(d, grupos, metodo, otros=()):
    d.update(grupos=_a_texto(grupos), metodo=metodo)
    via = {"foto": "por tu foto 📷", "audio": "por tu audio 🎙️"}.get(metodo, "por lo que escribiste")
    extra = f"\n{OTRO_TXT_CORTO.format(', '.join(otros))}" if otros else ""
    if len(d["grupos"]) == 1:
        (c, o), = d["grupos"].items()
        que = f" ({o})" if o else ""
        return [f"Identifiqué {via}{que}: {NOMBRE_TIPO[c]}.{extra}\n¿Es correcto?\n*1* Sí  *2* No, es otro tipo"], "CONFIRMAR_TIPO", d
    return [f"Identifiqué {via} *dos tipos* de residuo, que recogen colectivos distintos:\n{_lista_grupos(d['grupos'])}{extra}\n"
            "Crearé *2 solicitudes* (una por colectivo) con la misma dirección y horario.\n"
            "¿Es correcto?\n*1* Sí  *2* No, corregir"], "CONFIRMAR_TIPO", d


def _preguntar_duda(d):
    objeto = d["pendientes"][0]
    return [f"No logré clasificar *{objeto}*. ¿Qué es?\n*1* Orgánico  *2* Reciclable  *3* Ninguno (va a la basura ordinaria)"], "ITEM_DUDA", d


def _resultado_residuo(d, r, error, volver_menu):
    """Respuesta común a RESIDUO/FOTO (solicitud) y CLASIFICAR (solo consulta). `r` viene de core.segmentar."""
    if error:
        return [error], None, d
    g = r["grupos"]
    conocidos = {c: g[c] for c in CATS if g[c]}
    if not conocidos and g["OTRO"] and not g["DUDA"]:
        return [OTRO_TXT + "\nEscribe *menú* para volver."], "MENU", {}
    if not conocidos and not g["DUDA"]:
        if r["metodo"] == "foto":
            return ["No distingo el residuo en la foto. Toma otra más cerca y con buena luz 📷"], "FOTO", d
        return ["No te entendí qué residuos tienes. Cuéntamelo de nuevo (por ejemplo: _cáscaras de banano y hojas de papel_) "
                "o envíame una foto 📷"], "FOTO", d
    if not conocidos:  # solo dudas
        return ["No logré identificar ese residuo solo con el texto.\n📷 *Envíame una foto* o dime si es *orgánico* o *reciclable*."], "FOTO", d
    if volver_menu:
        if g["DUDA"]:
            conocidos_txt = _lista_grupos(_a_texto(conocidos))
            return [f"Identifiqué:\n{conocidos_txt}\nPero no logré clasificar: {', '.join(g['DUDA'])}. "
                    "Ante la duda, pregunta al coordinador.\nEscribe *1* si quieres solicitar la recolección."], "MENU", {}
        if len(conocidos) == 1 and len(next(iter(conocidos.values()))) == 1:
            (c, (o,)), = conocidos.items()
            que = f" ({o})" if o and r["metodo"] == "foto" else ""
            return [f"Eso parece {NOMBRE_TIPO[c]}{que}. Es una orientación: ante la duda, pregunta al coordinador.\n"
                    f"Lo recogen los *{_ahora_tipo(c)}*. Escribe *1* si quieres solicitar la recolección."], "MENU", {}
        return [f"Identifiqué:\n{_lista_grupos(_a_texto(conocidos))}\nEs una orientación: ante la duda, pregunta al coordinador.\n"
                "Escribe *1* si quieres solicitar la recolección."], "MENU", {}
    d.update(pendientes=list(g["DUDA"]), tmp_grupos={c: list(o) for c, o in conocidos.items()},
             tmp_metodo=r["metodo"], tmp_otros=list(g["OTRO"]))
    if d["pendientes"]:
        return _preguntar_duda(d)
    return _pedir_confirmacion(d, d.pop("tmp_grupos"), d.pop("tmp_metodo"), d.pop("tmp_otros"))


def _paso(paso, d, contacto, t, texto, foto, clasificar_foto, segmentar_foto, origen):
    n = NUMEROS.get(t)
    if paso == "MENU":
        if foto is None and n == 1:
            return ["¿Quién pide la recolección?\n*1* Hogar\n*2* Negocio o unidad productiva"], "GENERADOR", {}
        if foto is None and n == 2:
            return _consultar(contacto, t, texto), "MENU", {}
        if foto is None and n == 3:
            return [f"⭐ Tienes *{backend.puntos(contacto)} puntos*. Se suman cuando se registra una recolección. "
                    "(La regla de puntos aún está en validación.)"], "MENU", {}
        if foto is None and n == 4:
            lista = "\n".join(f"*{i}* {tt}" for i, (tt, _) in enumerate(contenido.TEMAS, 1))
            return [f"¿Qué quieres aprender?\n{lista}"], "APRENDER", {}
        if foto is None and n == 5:
            return ["Escríbeme qué residuo es (por ejemplo: _cáscara de banano_) o envíame una foto 📷"], "CLASIFICAR", {}
        if foto is None and t.startswith("estado"):
            return _consultar(contacto, t, texto), "MENU", {}
        if foto is None and not texto:
            return [MENU], "MENU", {}
        paso = "CLASIFICAR"  # texto o foto sueltos en el menú: se toma como "¿qué residuo es?"
    if paso == "CLASIFICAR":
        if foto is None and t in {"organico", "reciclable"}:
            return [f"Anotado: {NOMBRE_TIPO[t.upper()]}. Lo recogen los *{_ahora_tipo(t.upper())}*. Escribe *1* para solicitar la recolección."], "MENU", {}
        r, err = _clasificar_entrada(texto, foto, clasificar_foto, segmentar_foto, origen)
        resp, p, dd = _resultado_residuo({}, r, err, volver_menu=True)
        return resp, p or "CLASIFICAR", dd
    if paso == "APRENDER":
        if n and 1 <= n <= len(contenido.TEMAS):
            tt, cuerpo = contenido.TEMAS[n - 1]
            return [f"*{tt}*\n{cuerpo}\n\nEscribe *menú* para volver."], "MENU", {}
        return ["Responde con el número del tema o escribe *menú*."], "APRENDER", d
    if paso == "GENERADOR":
        if n in (1, 2):
            d["generador"] = "hogar" if n == 1 else "negocio"
            return ["Cuéntame qué residuo quieres entregar (por ejemplo: _cáscaras de banano y hojas de papel_). Puedes mencionar *varios* a la vez, "
                    "y enviarme un *audio* 🎙️ o una *foto* 📷"], "RESIDUO", d
        return ["Responde *1* (Hogar) o *2* (Negocio o unidad productiva)."], "GENERADOR", d
    if paso in ("RESIDUO", "FOTO"):
        manual = _tipo_manual(t) if foto is None and not t.isdigit() else None
        if manual:
            d.update(grupos={manual: ""}, metodo="usuario")
            return [f"Anotado: {NOMBRE_TIPO[manual]}. ¿Cuál es la *dirección* donde recogeríamos? (barrio, calle y número)"], "DIRECCION", d
        r, err = _clasificar_entrada(texto, foto, clasificar_foto, segmentar_foto, origen)
        resp, p, dd = _resultado_residuo(d, r, err, volver_menu=False)
        return resp, p or paso, dd
    if paso == "ITEM_DUDA":
        c = {"1": "ORGANICO", "organico": "ORGANICO", "2": "RECICLABLE", "reciclable": "RECICLABLE",
             "3": None, "ninguno": None, "basura": None, "ordinario": None}
        if t not in c:
            return ["Responde *1* (orgánico), *2* (reciclable) o *3* (ninguno)."], "ITEM_DUDA", d
        objeto = d["pendientes"].pop(0)
        if c[t]:
            d["tmp_grupos"].setdefault(c[t], []).append(objeto)
        else:
            d["tmp_otros"].append(objeto)
        if d["pendientes"]:
            return _preguntar_duda(d)
        if not d["tmp_grupos"]:
            return [OTRO_TXT + "\nEscribe *menú* para volver."], "MENU", {}
        for k in ("pendientes",):
            d.pop(k)
        return _pedir_confirmacion(d, d.pop("tmp_grupos"), d.pop("tmp_metodo"), d.pop("tmp_otros"))
    if paso == "CONFIRMAR_TIPO":
        if t in SI:
            return ["Perfecto. ¿Cuál es la *dirección* donde recogeríamos? (barrio, calle y número)"], "DIRECCION", d
        if t in NO and len(d.get("grupos", {})) > 1:
            d.pop("grupos", None)
            return ["Cuéntame de nuevo qué residuos son (texto, audio 🎙️ o foto 📷), o escribe *orgánico* / *reciclable* "
                    "si es de un solo tipo."], "RESIDUO", d
        if t in NO:
            return ["¿Entonces es?\n*1* Orgánico (restos de comida, cáscaras, poda)\n*2* Reciclable (plástico, vidrio, papel, metal)"], "TIPO_MANUAL", d
        return ["Responde *1* (sí, es correcto) o *2* (no)."], "CONFIRMAR_TIPO", d
    if paso == "TIPO_MANUAL":
        c = _tipo_manual(t)
        if c:
            d.update(grupos={c: ""}, metodo="usuario")
            return [f"Anotado: {NOMBRE_TIPO[c]}. ¿Cuál es la *dirección* donde recogeríamos? (barrio, calle y número)"], "DIRECCION", d
        return ["Responde *1* (orgánico) o *2* (reciclable)."], "TIPO_MANUAL", d
    if paso == "DIRECCION":
        if len((texto or "").strip()) >= 6:
            d["direccion"] = texto.strip()
            return ["¿Qué días y horas te sirven? (por ejemplo: _lunes y miércoles por la mañana_)"], "DISPONIBILIDAD", d
        return ["Necesito una dirección más completa (barrio, calle y número)."], "DIRECCION", d
    if paso == "DISPONIBILIDAD":
        if len((texto or "").strip()) >= 3:
            d["disponibilidad"] = texto.strip()
            return ["¿Algo más que debamos saber? (cantidad aproximada, cómo llegar…) o escribe *omitir*"], "OBSERVACIONES", d
        return ["Cuéntame qué días y horas te sirven."], "DISPONIBILIDAD", d
    if paso == "OBSERVACIONES":
        d["observaciones"] = "" if t in {"omitir", "no", "ninguna", "ninguno", "nada"} else (texto or "").strip()
        gen = "Hogar" if d["generador"] == "hogar" else "Negocio / unidad productiva"
        multiples = len(d["grupos"]) > 1
        cierre = ("Se crearán *2 solicitudes*, una para cada coordinador (huerteros y recicladores)." if multiples
                  else f"Irá al coordinador de *{_ahora_tipo(next(iter(d['grupos'])))}*.")
        resumen = (f"Revisa tu solicitud:\n• Quién pide: {gen}\n• Residuo:\n{_lista_grupos(d['grupos'])}\n"
                   f"• Dirección: {d['direccion']}\n• Disponibilidad: {d['disponibilidad']}\n"
                   f"• Observaciones: {d['observaciones'] or '—'}\n{cierre}\n*1* Confirmar  *2* Cancelar")
        return [resumen], "CONFIRMAR", d
    if paso == "CONFIRMAR":
        if t in SI:
            hechas = d.setdefault("hechas", {})  # si falla a medias, al reintentar no se duplican las ya creadas
            for cat, objeto in d["grupos"].items():
                if cat in hechas:
                    continue
                try:
                    s = backend.crear_solicitud({
                        "contacto": contacto, "canal": "whatsapp", "generador": d["generador"], "categoria": cat,
                        "objeto": objeto, "metodo": d.get("metodo", ""), "direccion": d["direccion"],
                        "disponibilidad": d["disponibilidad"], "observaciones": d.get("observaciones", "")})
                except core.DatosInvalidos as e:
                    return [f"No pude registrar la solicitud: {e}. Escribe *menú* para empezar de nuevo."], "MENU", {}
                except Exception:  # noqa: BLE001
                    log.exception("No se pudo crear la solicitud")
                    return ["No pude registrar la solicitud ahora. Intenta confirmar de nuevo (*1*) en un momento."], "CONFIRMAR", d
                hechas[cat] = [s["codigo"], s["flujo"]]
            if len(hechas) == 1:
                codigo, flujo = next(iter(hechas.values()))
                return [f"✅ Solicitud *{codigo}* recibida. Va al coordinador de *{flujo}*, que asignará a una persona "
                        "y acordará contigo día y hora. Te avisaré por aquí. Consulta el avance con *2*."], "MENU", {}
            lista = "\n".join(f"• *{c}* → {f}" for c, f in hechas.values())
            return [f"✅ Creé *{len(hechas)} solicitudes* (una por colectivo):\n{lista}\nCada coordinador asignará a una persona "
                    "y acordará contigo día y hora. Te avisaré por aquí. Consulta el avance con *2*."], "MENU", {}
        if t in NO:
            return ["Listo, no se creó la solicitud. Escribe *menú* para volver."], "MENU", {}
        return ["Responde *1* para confirmar o *2* para cancelar."], "CONFIRMAR", d
    return [MENU], "MENU", {}


def atender(contacto, texto=None, foto=None, clasificar_foto=None, segmentar_foto=None, origen="texto"):
    """Procesa UN mensaje (texto, texto de un audio con origen="audio", o foto) de `contacto` y devuelve los mensajes a responder."""
    if not habilitado(contacto):
        return [NO_HABILITADO]
    t = normalizar(texto or "")
    paso, d = db.cargar_conv(contacto)
    if foto is None and t in SALIDAS:
        db.guardar_conv(contacto, "MENU", {})
        return [("Listo, volvimos al inicio.\n\n" if t in {"cancelar", "salir", "volver"} else "") + MENU]
    if foto is None and t.startswith("estado") and paso != "MENU":
        return _consultar(contacto, t, texto)  # se puede consultar sin perder el avance de una solicitud
    resp, paso, d = _paso(paso, d, contacto, t, texto, foto, clasificar_foto, segmentar_foto, origen)
    db.guardar_conv(contacto, paso, d)
    return resp

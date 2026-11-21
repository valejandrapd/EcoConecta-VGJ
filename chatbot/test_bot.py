import pytest

import backend
import bot
import conversacion
import core
import db
import transcripcion
import vision
from clasificador import clasificar_texto


@pytest.fixture(autouse=True)
def base_limpia(monkeypatch):
    db.iniciar()
    db.vaciar()
    monkeypatch.delenv("PILOTO_NUMEROS", raising=False)
    monkeypatch.delenv("BACKEND_URL", raising=False)


class Chat:
    """Simula a una persona hablando con el bot (dependencias externas falsas)."""
    def __init__(self, tel="573106531916", foto=("RECICLABLE", "botella")):
        self.tel, self.foto, self.enviados = tel, foto, []

    def clasificar(self, datos, mime):
        if isinstance(self.foto, Exception):
            raise self.foto
        return self.foto

    def _msg(self, tipo, **extra):
        return {"id": str(len(self.enviados)), "from_me": False, "type": tipo, "chat_id": f"{self.tel}@s.whatsapp.net", **extra}

    def dice(self, texto):
        n = len(self.enviados)
        bot.procesar(self._msg("text", text={"body": texto}), lambda d, t: self.enviados.append(t),
                     lambda i: (b"x", "image/jpeg"), self.clasificar)
        return "\n".join(self.enviados[n:])

    def manda_foto(self):
        n = len(self.enviados)
        bot.procesar(self._msg("image", image={"id": "m1"}), lambda d, t: self.enviados.append(t),
                     lambda i: (b"x", "image/jpeg"), self.clasificar)
        return "\n".join(self.enviados[n:])


def solicitar_hasta_confirmar(c, residuo="cáscaras de banano", generador="2"):
    c.dice("hola"), c.dice("1"), c.dice(generador), c.dice(residuo)
    c.dice("1")  # confirma el tipo
    c.dice("Calle 45 #12-30, Villas de San Pablo")
    c.dice("lunes en la mañana")
    return c.dice("omitir")


# ---- clasificador de texto
@pytest.mark.parametrize("t,esperado", [
    ("cáscara de banano", "ORGANICO"), ("Sobras de comida", "ORGANICO"), ("botella de plástico", "RECICLABLE"),
    ("Una lata de aluminio", "RECICLABLE"), ("cuaderno viejo", "RECICLABLE"),
    ("no sé qué es esto, te cuento luego", None), ("algo raro", None),
])
def test_clasificar_texto(t, esperado):
    assert clasificar_texto(t) == esperado


# ---- flujo completo
def test_solicitud_organica_completa_se_enruta_a_huerteros():
    c = Chat()
    resumen = solicitar_hasta_confirmar(c)
    assert "Negocio" in resumen and "ORGÁNICO" in resumen and "huerteros" in resumen
    final = c.dice("1")
    assert "RES-" in final and "huerteros" in final
    s = core.listar(contacto=c.tel)[0]
    assert (s["flujo"], s["categoria"], s["generador"], s["canal"], s["estado"]) == ("huerteros", "ORGANICO", "negocio", "whatsapp", "recibida")
    assert s["direccion"].startswith("Calle 45") and s["disponibilidad"] == "lunes en la mañana"
    assert s["metodo"] == "texto"
    assert core.consultar(s["codigo"], con_historial=True)["historial"][0]["estado"] == "recibida"


def test_solicitud_reciclable_va_a_recicladores_y_ids_son_unicos():
    a, b = Chat("573001"), Chat("573002")
    for c in (a, b):
        solicitar_hasta_confirmar(c, residuo="botellas de plástico", generador="1")
        c.dice("1")
    sa, sb = core.listar(contacto="573001")[0], core.listar(contacto="573002")[0]
    assert sa["flujo"] == sb["flujo"] == "recicladores" and sa["codigo"] != sb["codigo"]


def test_texto_dudoso_pide_foto_y_la_foto_sugiere_tipo():
    c = Chat(foto=("ORGANICO", "cáscara de papa"))
    c.dice("hola"), c.dice("1"), c.dice("1")
    r = c.dice("esto de aquí")
    assert "foto" in r.lower()
    r = c.manda_foto()
    assert "ORGÁNICO" in r and "cáscara de papa" in r and "¿Es correcto?" in r
    assert "dirección" in c.dice("1")


def test_la_persona_puede_corregir_el_tipo_sugerido():
    c = Chat(foto=("ORGANICO", "algo"))
    c.dice("1"), c.dice("1"), c.dice("2"), c.manda_foto()
    assert "Reciclable" in c.dice("2")  # "No, es otro tipo"
    r = c.dice("2")
    assert "RECICLABLE" in r and "dirección" in r
    c.dice("Carrera 8 #5-10 barrio Centro"), c.dice("martes tarde"), c.dice("omitir")
    c.dice("1")
    s = core.listar(contacto=c.tel)[0]
    assert s["categoria"] == "RECICLABLE" and s["metodo"] == "usuario"


def test_decir_organico_o_reciclable_directamente():
    c = Chat()
    c.dice("1"), c.dice("1")
    assert "dirección" in c.dice("orgánico")
    assert list(db.cargar_conv(c.tel)[1]["grupos"]) == ["ORGANICO"]


def test_foto_borrosa_pide_otra():
    c = Chat(foto=("NO_SE_VE", ""))
    c.dice("1"), c.dice("1")
    assert "otra" in c.manda_foto()
    assert db.cargar_conv(c.tel)[0] == "FOTO"


def test_residuo_no_aprovechable_no_genera_solicitud():
    c = Chat(foto=("OTRO", "pañal"))
    c.dice("1"), c.dice("1")
    assert "no aprovechable" in c.manda_foto()
    assert core.listar(contacto=c.tel) == []


def test_error_al_procesar_la_foto_responde_amable_y_sigue_en_el_paso():
    c = Chat(foto=RuntimeError("API caída"))
    c.dice("1"), c.dice("1")
    assert "No pude procesar" in c.manda_foto()
    assert db.cargar_conv(c.tel)[0] == "RESIDUO"


def test_validaciones_de_direccion_y_opciones():
    c = Chat()
    c.dice("1")
    assert "Responde *1*" in c.dice("quizá")
    c.dice("1"), c.dice("botella"), c.dice("1")
    assert "dirección más completa" in c.dice("casa")


def test_cancelar_en_la_confirmacion_no_crea_nada():
    c = Chat()
    solicitar_hasta_confirmar(c)
    assert "no se creó" in c.dice("2")
    assert core.listar(contacto=c.tel) == []


def test_menu_cancelar_reinicia_el_flujo():
    c = Chat()
    c.dice("1"), c.dice("2")
    assert "volvimos al inicio" in c.dice("cancelar")
    assert db.cargar_conv(c.tel)[0] == "MENU"


# ---- consultas, privacidad y puntos
def test_consultar_estado_y_programacion():
    c = Chat()
    solicitar_hasta_confirmar(c), c.dice("1")
    s = core.listar(contacto=c.tel)[0]
    core.asignar(s["codigo"], "Coord", "Ana"), core.programar(s["codigo"], "martes 24", "8:00 a. m.")
    r = c.dice("2")
    assert s["codigo"] in r and "Programada" in r and "Ana" in r
    assert "Programada" in c.dice(f"estado {s['codigo']}")


def test_no_se_puede_ver_la_solicitud_de_otra_persona():
    dueno, intruso = Chat("573001"), Chat("573999")
    solicitar_hasta_confirmar(dueno), dueno.dice("1")
    codigo = core.listar(contacto="573001")[0]["codigo"]
    assert "No encontré" in intruso.dice(f"estado {codigo}")
    assert "Aún no tienes" in intruso.dice("2")


def test_puntos_solo_tras_recolectar():
    c = Chat()
    solicitar_hasta_confirmar(c), c.dice("1")
    codigo = core.listar(contacto=c.tel)[0]["codigo"]
    assert "0 puntos" in c.dice("3")
    core.asignar(codigo, "Coord", "Ana"), core.programar(codigo, "martes", "8:00"), core.recolectar(codigo, 4)
    assert "puntos" in c.dice("3") and "0 puntos" not in c.dice("3")


def test_aprender_muestra_contenido():
    c = Chat()
    assert "separar" in c.dice("4").lower()
    assert "Orgánicos" in c.dice("1")


def test_pregunta_suelta_de_residuo_orienta_sin_crear_solicitud():
    c = Chat()
    r = c.dice("una botella de plástico")
    assert "RECICLABLE" in r and "recicladores" in r
    assert core.listar(contacto=c.tel) == []


# ---- piloto, grupos, tipos no soportados
def test_usuarios_piloto(monkeypatch):
    monkeypatch.setenv("PILOTO_NUMEROS", "573001, +57 300 2")
    assert "no está habilitado" in Chat("573555").dice("hola")
    assert "EcoConecta" in Chat("573001").dice("hola")


def test_ignora_mensajes_propios_y_grupos():
    c = Chat()
    for ajuste in ({"from_me": True}, {"chat_id": "120363@g.us"}):
        msg = c._msg("text", text={"body": "hola"})
        msg.update(ajuste)
        bot.procesar(msg, lambda d, t: c.enviados.append(t), None, None)
    assert c.enviados == []


def test_audio_sin_transcripcion_configurada_avisa():
    c = Chat()
    bot.procesar(c._msg("voice", voice={"id": "a1"}), lambda d, t: c.enviados.append(t), None, None)
    assert "audios" in c.enviados[0] and "Escríbeme" in c.enviados[0]


def test_video_u_otro_tipo_responde_ayuda():
    c = Chat()
    bot.procesar(c._msg("video"), lambda d, t: c.enviados.append(t), None, None)
    assert "texto" in c.enviados[0] and "audios" in c.enviados[0]


# ---- varios residuos a la vez: una solicitud por tipo (huerteros / recicladores)
MEZCLA = "tengo cáscaras de banano y hojas de papel"


def pedir_mezcla(c, residuo=MEZCLA):
    c.dice("hola"), c.dice("1"), c.dice("1")
    return c.dice(residuo)


def test_texto_con_dos_tipos_crea_dos_solicitudes_una_por_colectivo():
    c = Chat()
    r = pedir_mezcla(c)
    assert "ORGÁNICO" in r and "RECICLABLE" in r and "2 solicitudes" in r
    assert "cáscaras de banano" in r and "hojas de papel" in r
    c.dice("1"), c.dice("Calle 45 #12-30 Villas"), c.dice("lunes en la mañana")
    resumen = c.dice("omitir")
    assert "2 solicitudes" in resumen and "huerteros" in resumen and "recicladores" in resumen
    final = c.dice("1")
    assert final.count("RES-") == 2
    por_flujo = {s["flujo"]: s for s in core.listar(contacto=c.tel)}
    assert set(por_flujo) == {"huerteros", "recicladores"}
    assert por_flujo["huerteros"]["objeto"] == "cáscaras de banano" and por_flujo["huerteros"]["categoria"] == "ORGANICO"
    assert por_flujo["recicladores"]["objeto"] == "hojas de papel" and por_flujo["recicladores"]["categoria"] == "RECICLABLE"
    assert por_flujo["huerteros"]["direccion"] == por_flujo["recicladores"]["direccion"]
    assert db.cargar_conv(c.tel)[0] == "MENU"


def test_corregir_una_mezcla_vuelve_a_pedir_los_residuos():
    c = Chat()
    pedir_mezcla(c)
    assert "de nuevo" in c.dice("2")
    assert db.cargar_conv(c.tel)[0] == "RESIDUO"
    assert "ORGÁNICO" in c.dice("cáscaras de naranja")


def test_si_falla_a_medias_al_reintentar_no_se_duplica(monkeypatch):
    c = Chat()
    pedir_mezcla(c)
    c.dice("1"), c.dice("Calle 45 #12-30 Villas"), c.dice("lunes"), c.dice("omitir")
    real, n = backend.crear_solicitud, {"v": 0}

    def inestable(datos):
        n["v"] += 1
        if n["v"] == 2:
            raise RuntimeError("caído")
        return real(datos)
    monkeypatch.setattr(backend, "crear_solicitud", inestable)
    assert "No pude registrar" in c.dice("1")
    assert len(core.listar(contacto=c.tel)) == 1
    assert c.dice("1").count("RES-") == 2
    assert len(core.listar(contacto=c.tel)) == 2


def test_item_dudoso_se_pregunta_y_uno_no_aprovechable_no_genera_solicitud(monkeypatch):
    c = Chat()
    c.dice("hola"), c.dice("1"), c.dice("1")
    r = c.dice("cáscaras de banano y un trapo viejo")
    assert "trapo viejo" in r and "Ninguno" in r
    r = c.dice("3")
    assert "ORGÁNICO" in r and "¿Es correcto?" in r
    assert "RECICLABLE" not in r


def test_item_dudoso_que_la_persona_clasifica():
    c = Chat()
    c.dice("hola"), c.dice("1"), c.dice("1")
    assert "algo raro" in c.dice("botella de plástico y algo raro")
    assert db.cargar_conv(c.tel)[0] == "ITEM_DUDA"
    r = c.dice("1")  # "algo raro" es orgánico
    assert "2 solicitudes" in r and "ORGÁNICO" in r and "RECICLABLE" in r


def test_mezcla_en_el_menu_solo_orienta():
    c = Chat()
    c.dice("hola")
    r = c.dice(MEZCLA)
    assert "ORGÁNICO" in r and "RECICLABLE" in r and "*1*" in r
    assert core.listar(contacto=c.tel) == []


def test_segmentar_por_palabras_clave():
    import segmentar
    assert segmentar.segmentar_por_palabras("Tengo cáscaras de banano, hojas de papel y botellas de plástico") == [
        {"objeto": "cáscaras de banano", "categoria": "ORGANICO"},
        {"objeto": "hojas de papel", "categoria": "RECICLABLE"},
        {"objeto": "botellas de plástico", "categoria": "RECICLABLE"}]
    assert segmentar.agrupar(segmentar.segmentar_por_palabras("pan y pan"))["ORGANICO"] == ["pan"]


@pytest.mark.parametrize("crudo,esperado", [
    ('{"items":[{"objeto":"cáscara","categoria":"organico"},{"objeto":"lata","categoria":"RECICLABLE"}]}',
     [{"objeto": "cáscara", "categoria": "ORGANICO"}, {"objeto": "lata", "categoria": "RECICLABLE"}]),
    ('```json\n{"items":[{"objeto":"x","categoria":"MARCIANO"}]}\n```', [{"objeto": "x", "categoria": "DUDA"}]),
    ('{"items": []}', []), ("nada", []), ('{"items": ["texto suelto"]}', []),
])
def test_interpretar_segmentos(crudo, esperado):
    import segmentar
    assert segmentar.interpretar(crudo) == esperado


# ---- audios: se transcriben y siguen el mismo flujo
class ChatAudio(Chat):
    def __init__(self, transcripcion="", **kw):
        super().__init__(**kw)
        self.transcripcion = transcripcion

    def manda_audio(self, tipo="voice", seconds=5):
        n = len(self.enviados)
        bot.procesar(self._msg(tipo, **{tipo: {"id": "a1", "seconds": seconds}}), lambda d, t: self.enviados.append(t),
                     lambda i: (b"x", "image/jpeg"), self.clasificar, None,
                     lambda datos, mime: self.transcripcion, lambda b: (b"audio", "audio/ogg"))
        return "\n".join(self.enviados[n:])


def test_audio_con_dos_residuos_se_entiende_y_se_separa():
    c = ChatAudio(MEZCLA)
    c.dice("hola"), c.dice("1"), c.dice("1")
    r = c.manda_audio()
    assert "Entendí" in r and MEZCLA in r and "por tu audio" in r and "2 solicitudes" in r
    c.dice("1"), c.dice("Calle 45 #12-30 Villas"), c.dice("lunes"), c.dice("omitir"), c.dice("1")
    assert {s["metodo"] for s in core.listar(contacto=c.tel)} == {"audio"}
    assert len(core.listar(contacto=c.tel)) == 2


def test_audio_puede_responder_pasos_como_direccion():
    c = ChatAudio("Calle 45 número 12 30 Villas de San Pablo")
    c.dice("hola"), c.dice("1"), c.dice("1"), c.dice("cáscaras de banano"), c.dice("1")
    r = c.manda_audio("ptt")
    assert "Entendí" in r and "días" in r.lower()


def test_audio_vacio_o_muy_largo():
    assert "No logré entender" in ChatAudio("  ").manda_audio()
    assert "muy largo" in ChatAudio("hola").manda_audio(seconds=900)


# ---- fotos con varios residuos
def test_foto_con_varios_residuos_se_separa():
    c = Chat()
    c.dice("hola"), c.dice("1"), c.dice("1")
    n = len(c.enviados)
    bot.procesar(c._msg("image", image={"id": "m1"}), lambda d, t: c.enviados.append(t), lambda i: (b"x", "image/jpeg"),
                 None, lambda datos, mime: [("ORGANICO", "cáscara de banano"), ("RECICLABLE", "hoja de papel"),
                                            ("OTRO", "colilla")])
    r = "\n".join(c.enviados[n:])
    assert "por tu foto" in r and "2 solicitudes" in r and "colilla" in r


# ---- modo remoto (backend real del equipo)
def test_el_bot_usa_el_backend_remoto_si_hay_backend_url(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://backend.test/api/v1")
    llamadas = []

    def falso(metodo, ruta, datos=None, consulta=None):
        llamadas.append((metodo, ruta, datos, consulta))
        if ruta == "/solicitudes" and metodo == "POST":
            return {"codigo": "RES-20261120-0099", "flujo": "huerteros"}
        return []
    monkeypatch.setattr(backend, "_http", falso)
    c = Chat()
    solicitar_hasta_confirmar(c)
    assert "RES-20261120-0099" in c.dice("1")
    post = [x for x in llamadas if x[0] == "POST"][0]
    assert post[2]["categoria"] == "ORGANICO" and post[2]["contacto"] == c.tel and post[2]["canal"] == "whatsapp"
    assert core.listar() == []  # nada se guardó en la base local


# ---- interpretación de la respuesta del modelo de visión
@pytest.mark.parametrize("crudo,esperado", [
    ('{"categoria": "ORGANICO", "objeto": "cáscara"}', ("ORGANICO", "cáscara")),
    ('Claro:\n```json\n{"categoria":"reciclable","objeto":"lata"}\n```', ("RECICLABLE", "lata")),
    ("no sé", ("NO_SE_VE", "")),
    ('{"categoria": "MARCIANO"}', ("NO_SE_VE", "")),
])
def test_interpretar_vision(crudo, esperado):
    assert vision.interpretar(crudo) == esperado

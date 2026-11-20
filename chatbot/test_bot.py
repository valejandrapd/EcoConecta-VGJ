import os

import pytest

import bot  # noqa: E402
import db  # noqa: E402
import vision  # noqa: E402
from clasificador import clasificar_texto  # noqa: E402


@pytest.fixture(autouse=True)
def base_limpia():
    if os.path.exists(db.ruta()):
        os.remove(db.ruta())
    db.iniciar()


class Falsos:
    """Dependencias externas simuladas."""
    def __init__(self, foto=("RECICLABLE", "botella")):
        self.enviados, self.foto = [], foto

    def enviar(self, destino, texto):
        self.enviados.append((destino, texto))

    def descargar(self, imagen):
        return b"bytes", "image/jpeg"

    def clasificar(self, datos, mime):
        if isinstance(self.foto, Exception):
            raise self.foto
        return self.foto


def texto(cuerpo, tel="573106531916"):
    return {"id": "1", "from_me": False, "type": "text", "chat_id": f"{tel}@s.whatsapp.net", "text": {"body": cuerpo}}


def foto(tel="573106531916"):
    return {"id": "2", "from_me": False, "type": "image", "chat_id": f"{tel}@s.whatsapp.net", "image": {"id": "m1"}}


def correr(msg, f):
    bot.procesar(msg, f.enviar, f.descargar, f.clasificar)


# ---- clasificador de texto
@pytest.mark.parametrize("t,esperado", [
    ("cáscara de banano", "ORGANICO"),
    ("Sobras de comida", "ORGANICO"),
    ("botella de plástico", "RECICLABLE"),
    ("Una lata de aluminio", "RECICLABLE"),
    ("cuaderno viejo", "RECICLABLE"),
    ("no sé qué es esto", None),
    ("algo raro", None),
])
def test_clasificar_texto(t, esperado):
    assert clasificar_texto(t) == esperado


# ---- flujo del bot
def test_texto_claro_responde_y_asigna_id():
    f = Falsos()
    correr(texto("cáscara de banano"), f)
    assert "ORGÁNICO" in f.enviados[0][1]
    assert "RES-" in f.enviados[0][1]
    assert db.obtener(f.enviados[0][1].split("*")[1])["categoria"] == "ORGANICO"


def test_ids_unicos():
    f = Falsos()
    correr(texto("botella de plástico"), f)
    correr(texto("botella de plástico"), f)
    ids = {t.split("*")[1] for _, t in f.enviados}
    assert len(ids) == 2


def test_texto_desconocido_pide_foto_y_luego_la_identifica():
    f = Falsos(foto=("ORGANICO", "cáscara de papa"))
    correr(texto("esto de aquí"), f)
    assert "Envíame una foto" in f.enviados[0][1]
    codigo = f.enviados[0][1].split("*")[1]
    assert db.obtener(codigo)["estado"] == "esperando_foto"

    correr(foto(), f)
    assert codigo in f.enviados[1][1]          # la foto resuelve LA MISMA solicitud
    assert "ORGÁNICO" in f.enviados[1][1]
    assert db.obtener(codigo)["metodo"] == "foto"


def test_foto_sin_solicitud_previa_crea_una():
    f = Falsos(foto=("RECICLABLE", "lata"))
    correr(foto(), f)
    assert "RECICLABLE" in f.enviados[0][1] and "RES-" in f.enviados[0][1]


def test_foto_borrosa_pide_otra_y_sigue_pendiente():
    f = Falsos(foto=("NO_SE_VE", ""))
    correr(texto("cosa rara"), f)
    codigo = f.enviados[0][1].split("*")[1]
    correr(foto(), f)
    assert "otra foto" in f.enviados[1][1]
    assert db.obtener(codigo)["estado"] == "esperando_foto"


def test_error_en_la_foto_responde_amable():
    f = Falsos(foto=RuntimeError("caída de la API"))
    correr(foto(), f)
    assert "no pude procesar la foto" in f.enviados[0][1]


def test_ignora_mensajes_propios_y_grupos():
    f = Falsos()
    propio = texto("botella")
    propio["from_me"] = True
    grupo = texto("botella")
    grupo["chat_id"] = "120363@g.us"
    correr(propio, f)
    correr(grupo, f)
    assert f.enviados == []


def test_consulta_de_estado():
    f = Falsos()
    correr(texto("botella de plástico"), f)
    codigo = f.enviados[0][1].split("*")[1]
    correr(texto(f"estado {codigo}"), f)
    assert "RECICLABLE" in f.enviados[1][1]
    correr(texto("estado RES-00000000-9999"), f)
    assert "No encontré" in f.enviados[2][1]


def test_ayuda_y_tipos_no_soportados():
    f = Falsos()
    correr(texto("hola"), f)
    audio = {"id": "3", "from_me": False, "type": "audio", "chat_id": "57310@s.whatsapp.net"}
    correr(audio, f)
    assert "EcoConecta" in f.enviados[0][1]
    assert "solo entiendo" in f.enviados[1][1]


# ---- interpretación de la respuesta del modelo de visión
@pytest.mark.parametrize("crudo,esperado", [
    ('{"categoria": "ORGANICO", "objeto": "cáscara"}', ("ORGANICO", "cáscara")),
    ('Claro:\n```json\n{"categoria":"reciclable","objeto":"lata"}\n```', ("RECICLABLE", "lata")),
    ("no sé", ("NO_SE_VE", "")),
    ('{"categoria": "MARCIANO"}', ("NO_SE_VE", "")),
])
def test_interpretar_vision(crudo, esperado):
    assert vision.interpretar(crudo) == esperado

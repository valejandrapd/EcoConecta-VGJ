"""Asistente de nueva solicitud por WhatsApp: mismos pasos que la web, con menú numérico."""
from datetime import time

import pytest

from sqlalchemy import select

from app.db import sesion
from app.models import ConversacionWhatsapp, DireccionUsuario, Solicitud, Usuario

from .conftest import ANA, BETO, EXTRANO, mensaje, publicar


@pytest.fixture(autouse=True)
def sin_limite_diario(monkeypatch):
    """Una solicitud completa por WhatsApp son ~10 mensajes; en pruebas el límite diario es 5."""
    from dataclasses import replace
    from app import config as modulo
    original = modulo.config()
    monkeypatch.setattr("app.whatsapp.bot.config", lambda: replace(original, limite_mensajes_dia=100))


def _hablar(client, wa, de, *textos):
    for t in textos:
        publicar(client, mensaje(de, texto=t))
    return wa.textos_a(de)[-1]


def _solicitudes(tel):
    with sesion() as s:
        filas = s.scalars(select(Solicitud).join(Usuario, Solicitud.usuario_id == Usuario.id)
                          .where(Usuario.telefono == "+" + tel).order_by(Solicitud.id)).all()
        s.expunge_all()
        return filas


def test_flujo_completo_con_su_direccion(client, wa):
    assert "¿Qué vas a entregar?" in _hablar(client, wa, ANA, "2")
    assert "Antes de entregarlo" in _hablar(client, wa, ANA, "2")       # reciclables -> consejos
    assert "PET" in wa.textos_a(ANA)[-1]
    assert "¿Qué tanto tienes?" in _hablar(client, wa, ANA, "1")         # ¡Entendido!
    assert "una botella o una lata" in wa.textos_a(ANA)[-1]
    assert "¿Qué días" in _hablar(client, wa, ANA, "2")                  # mediano
    r = _hablar(client, wa, ANA, "2, 4")                                  # mar y jue
    assert "Mar, Jue" in r and "¿A qué hora" in r
    r = _hablar(client, wa, ANA, "2")                                     # tarde
    assert "¿Estarás en esta dirección?" in r and "Calle 10 # 1-2 (Sector 1)" in r
    assert "¿Cómo quieres tus puntos?" in _hablar(client, wa, ANA, "1")  # sí, aquí
    r = _hablar(client, wa, ANA, "2")                                     # huerto
    assert "Revisa y confirma" in r and "Reciclable" in r and "12 m. a 5 p. m." in r
    r = _hablar(client, wa, ANA, "1")
    assert "¡Solicitud creada!" in r and "REC-0001" in r
    # El bot ya respondió con el código: no se manda además el aviso de "Recibimos tu solicitud"
    assert not any("Recibimos tu solicitud" in t for t in wa.textos_a(ANA))

    [sol] = _solicitudes(ANA)
    assert (sol.flujo, sol.tamano, sol.dias_disponibles, sol.bonificacion) == ("reciclable", "mediano", "mar,jue", "huerto")
    assert (sol.hora_desde, sol.hora_hasta, sol.zona, sol.direccion) == (time(12), time(17), "Sector 1", "Calle 10 # 1-2")
    with sesion() as s:
        conv = s.get(ConversacionWhatsapp, ANA)
        assert conv.estado is None and conv.borrador is None  # el borrador no queda guardado


def test_no_se_que_es_otra_direccion_y_nota(client, wa):
    _hablar(client, wa, BETO, "2", "3")
    r = _hablar(client, wa, BETO, "cáscaras de banano")                   # reglas: orgánico
    assert "ORGÁNICO" in r and "Sin etiquetas" in r
    _hablar(client, wa, BETO, "1", "3")                                    # grande
    _hablar(client, wa, BETO, "8")                                         # entre semana
    assert "Escribe desde qué hora" in _hablar(client, wa, BETO, "4")
    assert "¿Estarás en esta dirección?" in _hablar(client, wa, BETO, "2 a 5 pm")
    assert "dirección de recolección" in _hablar(client, wa, BETO, "2")
    assert "¿En qué zona queda?" in _hablar(client, wa, BETO, "Manzana 7, casa 3")
    assert "Ponle un nombre" in _hablar(client, wa, BETO, "3")             # Sector 3
    assert "¿Cómo quieres tus puntos?" in _hablar(client, wa, BETO, "1")   # Casa mamá
    _hablar(client, wa, BETO, "1")
    assert "Escribe la nota" in _hablar(client, wa, BETO, "2")
    r = _hablar(client, wa, BETO, "Timbre dañado, llamar al llegar")
    assert "Revisa y confirma" in r and "Casa mamá: Manzana 7, casa 3 · Sector 3" in r and "Timbre dañado" in r
    assert "ORG-0001" in _hablar(client, wa, BETO, "1")

    [sol] = _solicitudes(BETO)
    assert sol.dias_disponibles == "lun,mar,mie,jue,vie" and (sol.hora_desde, sol.hora_hasta) == (time(14), time(17))
    assert (sol.zona, sol.direccion_etiqueta, sol.observaciones) == ("Sector 3", "Casa mamá", "Timbre dañado, llamar al llegar")
    with sesion() as s:
        guardada = s.scalar(select(DireccionUsuario).where(DireccionUsuario.etiqueta == "Casa mamá"))
        assert guardada.direccion == "Manzana 7, casa 3"

    # La próxima vez la dirección guardada aparece como opción
    _hablar(client, wa, BETO, "2", "1", "1", "1", "1", "1")
    assert "🏷️ Casa mamá: Manzana 7, casa 3 (Sector 3)" in wa.textos_a(BETO)[-1]


def test_atras_error_y_menu(client, wa):
    _hablar(client, wa, ANA, "2", "1", "1")                               # orgánico, consejos, entendido
    r = _hablar(client, wa, ANA, "9")                                      # opción inexistente en tamaño
    assert "No te entendí" in r and "¿Qué tanto tienes?" in r
    assert "Antes de entregarlo" in _hablar(client, wa, ANA, "atrás")
    assert "¿Qué vas a entregar?" in _hablar(client, wa, ANA, "atras")
    # Dentro del asistente "1" es una opción, no "¿Qué es EcoConecta?"
    assert "Antes de entregarlo" in _hablar(client, wa, ANA, "1")
    assert "Responde con un número" in _hablar(client, wa, ANA, "menú")
    assert "EcoConecta conecta" in _hablar(client, wa, ANA, "1")          # fuera del asistente: menú normal
    assert _solicitudes(ANA) == []


def test_cancelar_en_resumen(client, wa):
    _hablar(client, wa, ANA, "2", "1", "1", "1", "10", "3", "1", "1")
    assert "Revisa y confirma" in wa.textos_a(ANA)[-1] and "Lun, Mar, Mié, Jue, Vie, Sáb, Dom" in wa.textos_a(ANA)[-1]
    assert "no creé la solicitud" in _hablar(client, wa, ANA, "3")
    assert _solicitudes(ANA) == []


def test_no_registrado_no_entra_al_asistente(client, wa):
    assert "no está registrado" in _hablar(client, wa, EXTRANO, "2")
    with sesion() as s:
        assert (s.get(ConversacionWhatsapp, EXTRANO).estado or "") == ""

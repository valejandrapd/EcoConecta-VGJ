"""Mejoras tomadas del bot del equipo: notas de voz y varios residuos en un mismo mensaje."""
import pytest
from sqlalchemy import select

from app.db import sesion
from app.ia import segmentar, transcripcion
from app.models import MensajeWhatsapp, Solicitud, Usuario

from .conftest import ANA, BETO, mensaje, publicar


@pytest.fixture(autouse=True)
def sin_limite_diario(monkeypatch):
    from dataclasses import replace
    from app import config as modulo
    original = modulo.config()
    monkeypatch.setattr("app.whatsapp.bot.config", lambda: replace(original, limite_mensajes_dia=100))


def _hablar(client, wa, de, *textos):
    for t in textos:
        publicar(client, mensaje(de, texto=t))
    return wa.textos_a(de)[-1]


def _codigos(tel):
    with sesion() as s:
        return [c for c in s.scalars(select(Solicitud.codigo).join(Usuario, Solicitud.usuario_id == Usuario.id)
                                     .where(Usuario.telefono == "+" + tel).order_by(Solicitud.id))]


def test_segmentar_agrupa_por_tipo_sin_ia():
    g = segmentar.agrupar("tengo cáscaras de banano, una botella y hojas de papel", usar_modelo=False)
    assert g["organico"] == ["cáscaras de banano"]
    assert g["reciclable"] == ["una botella", "hojas de papel"]
    assert segmentar.es_mezcla(g)


def test_mezcla_crea_una_solicitud_por_tipo_con_los_mismos_datos(client, wa):
    _hablar(client, wa, ANA, "2", "3")
    r = _hablar(client, wa, ANA, "cáscaras de banano y hojas de papel")
    assert "Encontré dos tipos" in r and "cáscaras de banano" in r and "hojas de papel" in r
    assert "Sin etiquetas" in r                                          # consejos de orgánicos
    _hablar(client, wa, ANA, "1", "2", "2, 4", "1", "1")                 # entendido, mediano, mar y jue, mañana, su dirección
    assert "Revisa y confirma" in _hablar(client, wa, ANA, "2")          # huerto
    r = _hablar(client, wa, ANA, "1")
    assert "ORG-0001" in r and "Reciclable" in r and "PET" in r          # creó la primera y pasa a la segunda
    assert "¿Qué tanto tienes?" in _hablar(client, wa, ANA, "1")
    r = _hablar(client, wa, ANA, "3")                                    # grande: va directo al resumen
    assert "Revisa y confirma" in r and "Reciclable" in r and "Mar, Jue" in r and "Servicios del huerto" in r
    assert "REC-0001" in _hablar(client, wa, ANA, "1")
    assert _codigos(ANA) == ["ORG-0001", "REC-0001"]


def test_audio_sigue_el_mismo_camino_que_el_texto(client, wa, monkeypatch):
    wa.media = b"OggS-falso"
    monkeypatch.setattr(transcripcion, "disponible", lambda: True)
    monkeypatch.setattr(transcripcion, "transcribir", lambda datos, mime: "2")
    publicar(client, mensaje(BETO, tipo="audio"))
    ultimo = wa.textos_a(BETO)[-1]
    assert "🎤" in ultimo and "¿Qué vas a entregar?" in ultimo
    with sesion() as s:  # del audio solo quedan metadatos, nunca el texto
        tipos = {m.tipo for m in s.scalars(select(MensajeWhatsapp).where(MensajeWhatsapp.wa_id == BETO))}
    assert "audio" in tipos


def test_audio_sin_transcripcion_configurada(client, wa, monkeypatch):
    monkeypatch.setattr(transcripcion, "disponible", lambda: False)
    publicar(client, mensaje(BETO, tipo="audio"))
    assert "texto" in wa.textos_a(BETO)[-1]

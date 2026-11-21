"""Consulta de estado (RN-07), contenidos y derivación a la coordinación."""
from datetime import time

from sqlalchemy import select

from app import solicitudes
from app.db import sesion
from app.models import CasoCoordinacion, Contenido, Usuario

from .conftest import ANA, BETO, mensaje, personal, proximo, publicar


FECHA = proximo("mie")


def _crear_programada(dueno_tel):
    with sesion() as s:
        dueno = s.scalar(select(Usuario).where(Usuario.telefono == "+" + dueno_tel))
        coord = s.scalar(select(Usuario).where(Usuario.rol == "coordinador_huerta"))
        sol = solicitudes.crear(s, dueno, "organico", observaciones="cáscaras")
        solicitudes.asignar(s, sol, coord, personal("Rosa").id)
        solicitudes.programar(s, sol, coord, FECHA, time(8, 30))
        return sol.codigo


def test_estado_dueno(client, wa):
    codigo = _crear_programada(ANA)
    publicar(client, mensaje(ANA, texto=f"estado {codigo}"))
    texto = wa.textos_a(ANA)[-1]
    assert codigo in texto and "Programada" in texto and f"{FECHA:%d/%m/%Y}" in texto and "08:30" in texto
    assert "Rosa" in texto and "Martínez" not in texto and "+57" not in texto


def test_estado_numero_ajeno_rechazado(client, wa):
    codigo = _crear_programada(ANA)
    publicar(client, mensaje(BETO, texto=f"estado {codigo}"))
    (texto,) = wa.textos_a(BETO)
    assert "No encontré" in texto
    assert "Programada" not in texto and "Calle 10" not in texto and "Ana" not in texto and ANA not in texto


def test_estado_codigo_inexistente_mismo_mensaje(client, wa):
    publicar(client, mensaje(ANA, texto="REC-9999"))
    assert "No encontré" in wa.textos_a(ANA)[0]


def test_contenidos_solo_de_la_tabla(client, wa):
    with sesion() as s:
        s.add(Contenido(tipo="horario", titulo="Horario orgánicos", cuerpo="Martes 7 a. m.", palabras_clave="horario"))
    publicar(client, mensaje(ANA, texto="¿cuál es el horario?"))
    assert "Martes 7 a. m." in wa.textos_a(ANA)[0]


def test_sin_contenido_deriva(client, wa):
    publicar(client, mensaje(ANA, texto="¿qué ruta pasa por mi sector?"))
    assert "coordinación" in wa.textos_a(ANA)[0]
    with sesion() as s:
        assert s.scalar(select(CasoCoordinacion.motivo)) == "sin_contenido"


def test_pide_persona_registra_caso(client, wa):
    _crear_programada(ANA)
    publicar(client, mensaje(ANA, texto="quiero hablar con una persona"))
    assert "coordinación de huerta te contactará" in wa.textos_a(ANA)[-1]
    with sesion() as s:
        caso = s.scalar(select(CasoCoordinacion))
    assert caso.motivo == "pidio_persona" and caso.flujo == "organico"


def test_dos_no_entendidos_derivan(client, wa):
    publicar(client, mensaje(ANA, texto="xyzzy"))
    publicar(client, mensaje(ANA, texto="qwerty"))
    textos = wa.textos_a(ANA)
    assert "No te entendí" in textos[0] and "te contactará" in textos[1]
    with sesion() as s:
        assert s.scalar(select(CasoCoordinacion.motivo)) == "no_entendido"


def test_codigos_por_flujo(client, wa):
    with sesion() as s:
        ana = s.scalar(select(Usuario).where(Usuario.telefono == "+" + ANA))
        a = solicitudes.crear(s, ana, "organico").codigo
        b = solicitudes.crear(s, ana, "reciclable").codigo
    assert a.startswith("ORG-") and b.startswith("REC-") and len(a) == 8

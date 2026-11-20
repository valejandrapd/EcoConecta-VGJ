"""Notificaciones (ventana de 24 h / plantillas) y cascada de IA."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app import solicitudes
from app.db import sesion
from app.ia import cascada, modelo
from app.models import ConversacionWhatsapp, Usuario
from app.notificaciones import LogNotificador, obtener_notificador
from app.telefono import normalizar

from .conftest import ANA, mensaje, publicar


def test_fuera_de_ventana_usa_plantilla(wa):
    with sesion() as s:
        ana = s.scalar(select(Usuario).where(Usuario.telefono == "+" + ANA))
        sol = solicitudes.crear(s, ana, "organico")
    plantillas = [e for e in wa.enviados if e[0] == "plantilla"]
    nombres = {e[2] for e in plantillas}
    assert nombres == {"solicitud_recibida", "nueva_solicitud"}
    assert all(sol.codigo in e[3] for e in plantillas)


def test_dentro_de_ventana_usa_texto(client, wa):
    publicar(client, mensaje(ANA, texto="hola"))  # abre la ventana
    with sesion() as s:
        ana = s.scalar(select(Usuario).where(Usuario.telefono == "+" + ANA))
        solicitudes.crear(s, ana, "reciclable")
    assert any("Recibimos tu solicitud" in t for t in wa.textos_a(ANA))


def test_ventana_vencida(client, wa):
    publicar(client, mensaje(ANA, texto="hola"))
    with sesion() as s:
        s.get(ConversacionWhatsapp, ANA).ultimo_entrante_en = datetime.now(timezone.utc) - timedelta(hours=25)
    with sesion() as s:
        ana = s.scalar(select(Usuario).where(Usuario.telefono == "+" + ANA))
        solicitudes.crear(s, ana, "organico")
    assert ("plantilla", ANA) in {(e[0], e[1]) for e in wa.enviados}


def test_log_notificador_por_defecto():
    from app.whatsapp import cliente
    cliente.usar_cliente(None)
    assert isinstance(obtener_notificador(), LogNotificador)


def test_cascada_reglas_no_llama_ia(monkeypatch):
    monkeypatch.setattr(modelo, "clasificar_texto", lambda t: (_ for _ in ()).throw(AssertionError("no")))
    s = cascada.sugerir_texto("botella de plástico")
    assert s.categoria == "reciclable" and s.confianza == "alta" and s.origen == "reglas"


def test_cascada_pasa_al_modelo_de_texto(monkeypatch):
    enviado = {}

    def falso(t):
        enviado["t"] = t
        return {"categoria": "NO_APROVECHABLE", "objeto": "pañal", "confianza": "media"}

    monkeypatch.setattr(modelo, "clasificar_texto", falso)
    s = cascada.sugerir_texto("un pañal usado")
    assert s.origen == "modelo_texto" and s.categoria == "no_aprovechable" and enviado["t"] == "un pañal usado"


def test_sin_clave_ia_no_disponible():
    import pytest
    with pytest.raises(modelo.IANoDisponible):
        modelo.clasificar_texto("algo")


def test_interpretar_tolera_basura():
    assert modelo.interpretar("nada")["categoria"] == "DESCONOCIDO"
    r = modelo.interpretar('ok {"categoria":"organico","objeto":"cáscara","confianza":"ALTA"}')
    assert r == {"categoria": "ORGANICO", "objeto": "cáscara", "confianza": "alta"}


def test_normalizar_telefono():
    assert normalizar("573001112233") == "+573001112233"
    assert normalizar("300 111 2233") == "+573001112233"
    assert normalizar("+57 (300) 111-2233") == "+573001112233"
    assert normalizar("abc") == ""

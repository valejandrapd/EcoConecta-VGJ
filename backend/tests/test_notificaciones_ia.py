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


def test_azure_openai_traduce_texto_e_imagen(monkeypatch):
    """Con IA_PROVEEDOR=azure_openai se usa el SDK oficial de OpenAI con el mismo contrato."""
    from dataclasses import replace
    from types import SimpleNamespace
    import openai
    from app import config as cfg_mod

    original = cfg_mod.config()
    monkeypatch.setattr(modelo, "config", lambda: replace(
        original, ia_proveedor="azure_openai", azure_openai_endpoint="https://eco.openai.azure.com",
        azure_openai_api_key="k", azure_openai_deployment="gpt-4o-mini"))
    pedidos = []

    class Falso:
        def __init__(self, **kw):
            pedidos.append(kw)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.crear))

        def crear(self, **kw):
            pedidos.append(kw)
            msg = SimpleNamespace(content='{"categoria":"RECICLABLE","objeto":"botella","confianza":"alta"}')
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")])

    monkeypatch.setattr(openai, "AzureOpenAI", Falso)
    assert modelo.clasificar_texto("una botella")["categoria"] == "RECICLABLE"
    assert pedidos[0]["azure_endpoint"] == "https://eco.openai.azure.com"
    assert pedidos[1]["model"] == "gpt-4o-mini" and pedidos[1]["messages"][0]["role"] == "system"
    modelo.clasificar_imagen(b"\xff\xd8jpeg")
    imagen = pedidos[3]["messages"][1]["content"][0]
    assert imagen["type"] == "image_url" and imagen["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_azure_openai_sin_clave_no_disponible(monkeypatch):
    from dataclasses import replace
    import pytest
    from app import config as cfg_mod
    original = cfg_mod.config()
    monkeypatch.setattr(modelo, "config", lambda: replace(original, ia_proveedor="azure_openai"))
    with pytest.raises(modelo.IANoDisponible):
        modelo.clasificar_texto("algo")

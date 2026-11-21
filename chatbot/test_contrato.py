"""Prueba de contrato: el bot habla por HTTP con un backend que cumple /api/v1 (aquí, el propio provisional)."""
import threading

import pytest
from werkzeug.serving import make_server

import app as servidor
import backend
import core
import db
import notificar
from test_bot import Chat, solicitar_hasta_confirmar


@pytest.fixture
def servidor_remoto(monkeypatch):
    db.iniciar()
    db.vaciar()
    srv = make_server("127.0.0.1", 0, servidor.app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("BACKEND_URL", f"http://127.0.0.1:{srv.server_port}/api/v1")
    monkeypatch.setattr(notificar.whapi, "enviar_texto", lambda d, t: None)
    yield
    srv.shutdown()


def test_el_bot_funciona_contra_un_backend_http(servidor_remoto):
    c = Chat()
    solicitar_hasta_confirmar(c)
    assert "RES-" in c.dice("1")
    s = core.listar(contacto=c.tel)[0]  # lo creó el backend remoto
    assert s["flujo"] == "huerteros"
    assert s["codigo"] in c.dice("2")
    assert "0 puntos" in c.dice("3")
    core.asignar(s["codigo"], "Coord", "Ana"), core.programar(s["codigo"], "martes", "8:00"), core.recolectar(s["codigo"], 2)
    assert "14 puntos" in c.dice("3")


def test_errores_del_backend_remoto_se_traducen(servidor_remoto):
    with pytest.raises(core.SolicitudNoEncontrada):
        backend.consultar("RES-00000000-0001", "573")
    with pytest.raises(core.DatosInvalidos):
        backend.crear_solicitud({"contacto": "573"})

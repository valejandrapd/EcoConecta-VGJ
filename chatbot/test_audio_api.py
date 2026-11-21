import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import app as servidor
import db
import transcripcion
import vision
import whapi


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    db.iniciar()
    db.vaciar()
    for v in ("API_KEY", "CORS_ORIGINS", "BACKEND_URL"):
        monkeypatch.delenv(v, raising=False)


@pytest.fixture
def cli():
    return servidor.app.test_client()


def test_segmentar_texto_por_api(cli):
    r = cli.post("/api/v1/segmentar", json={"texto": "cáscaras de banano y hojas de papel"})
    assert r.status_code == 200
    j = r.get_json()
    assert j["grupos"]["ORGANICO"] == ["cáscaras de banano"] and j["grupos"]["RECICLABLE"] == ["hojas de papel"]
    assert j["metodo"] == "texto"


def test_segmentar_pide_algo_y_valida(cli):
    assert cli.post("/api/v1/segmentar", json={}).status_code == 400


def test_segmentar_foto_por_api(cli, monkeypatch):
    monkeypatch.setattr(vision, "segmentar_foto", lambda d, m: [("ORGANICO", "cáscara"), ("RECICLABLE", "lata")])
    r = cli.post("/api/v1/segmentar", data={"foto": (io.BytesIO(b"x"), "f.jpg", "image/jpeg")},
                 content_type="multipart/form-data")
    j = r.get_json()
    assert r.status_code == 200 and j["metodo"] == "foto" and j["grupos"]["RECICLABLE"] == ["lata"]


def test_segmentar_audio_por_api(cli, monkeypatch):
    monkeypatch.setenv("STT_API_KEY", "k")
    monkeypatch.setattr(transcripcion, "transcribir", lambda d, m: "pan y una lata")
    r = cli.post("/api/v1/segmentar", data={"audio": (io.BytesIO(b"x"), "a.ogg", "audio/ogg")},
                 content_type="multipart/form-data")
    j = r.get_json()
    assert r.status_code == 200 and j["metodo"] == "audio" and j["transcripcion"] == "pan y una lata"
    assert j["grupos"]["ORGANICO"] == ["pan"] and j["grupos"]["RECICLABLE"] == ["una lata"]


def test_segmentar_audio_sin_stt_configurado(cli):
    r = cli.post("/api/v1/segmentar", data={"audio": (io.BytesIO(b"x"), "a.ogg", "audio/ogg")},
                 content_type="multipart/form-data")
    assert r.status_code == 503


def test_transcribir_envia_multipart_con_la_clave(monkeypatch):
    visto = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            visto["auth"] = self.headers["Authorization"]
            visto["tipo"] = self.headers["Content-Type"]
            visto["cuerpo"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"text": " hola mundo "}).encode())

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("STT_API_KEY", "clave-x")
    monkeypatch.setenv("STT_URL", f"http://127.0.0.1:{srv.server_port}/v1/audio/transcriptions")
    try:
        assert transcripcion.transcribir(b"AUDIOBYTES", "audio/ogg; codecs=opus") == "hola mundo"
    finally:
        srv.shutdown()
    assert visto["auth"] == "Bearer clave-x" and visto["tipo"].startswith("multipart/form-data")
    assert b"AUDIOBYTES" in visto["cuerpo"] and b'filename="audio.ogg"' in visto["cuerpo"] and b'name="language"' in visto["cuerpo"]


def test_descargar_audio_usa_el_bloque_voice(monkeypatch):
    monkeypatch.setenv("WHAPI_TOKEN", "t")
    llamado = []
    monkeypatch.setattr(whapi, "_pedir", lambda url, datos=None, con_token=True: llamado.append((url, con_token)) or b"ogg")
    assert whapi.descargar_audio({"id": "abc", "mime_type": "audio/ogg; codecs=opus"}) == (b"ogg", "audio/ogg")
    assert whapi.descargar_audio({"link": "http://x/y.ogg"})[0] == b"ogg"
    assert llamado[0][0].endswith("/media/abc") and llamado[1] == ("http://x/y.ogg", False)

import io
import os

import pytest

import app as servidor  # noqa: E402
import db  # noqa: E402
import vision  # noqa: E402


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    if os.path.exists(db.ruta()):
        os.remove(db.ruta())
    db.iniciar()
    for v in ("API_KEY", "CORS_ORIGINS"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(vision, "clasificar_foto", lambda datos, mime: ("RECICLABLE", "lata"))


@pytest.fixture
def cli():
    return servidor.app.test_client()


def foto(nombre="r.jpg", mime="image/jpeg", datos=b"\xff\xd8bytes"):
    return (io.BytesIO(datos), nombre, mime)


def multipart(**campos):
    return {k: v for k, v in campos.items()}


def test_texto_claro_se_resuelve(cli):
    r = cli.post("/api/v1/solicitudes", json={"contacto": "user-1", "texto": "cáscara de banano"})
    j = r.get_json()
    assert r.status_code == 201
    assert j["categoria"] == "ORGANICO" and j["metodo"] == "texto" and not j["necesita_foto"]
    assert j["codigo"].startswith("RES-") and j["canal"] == "api"


def test_texto_dudoso_pide_foto_y_la_foto_resuelve_la_misma(cli):
    j = cli.post("/api/v1/solicitudes", json={"contacto": "u1", "texto": "esto de aquí"}).get_json()
    assert j["necesita_foto"] and j["categoria"] is None
    r = cli.post(f"/api/v1/solicitudes/{j['codigo']}/foto",
                 data=multipart(foto=foto()), content_type="multipart/form-data")
    f = r.get_json()
    assert r.status_code == 200 and f["codigo"] == j["codigo"]
    assert f["categoria"] == "RECICLABLE" and f["metodo"] == "foto" and f["objeto"] == "lata"


def test_texto_y_foto_en_una_sola_peticion(cli):
    r = cli.post("/api/v1/solicitudes", content_type="multipart/form-data",
                 data=multipart(contacto="u1", texto="cosa rara", foto=foto()))
    j = r.get_json()
    assert r.status_code == 201 and j["metodo"] == "foto" and j["estado"] == "resuelta"


def test_solo_foto_crea_solicitud(cli):
    r = cli.post("/api/v1/solicitudes", content_type="multipart/form-data",
                 data=multipart(contacto="u1", foto=foto()))
    assert r.status_code == 201 and r.get_json()["categoria"] == "RECICLABLE"


def test_foto_ilegible_sigue_pendiente(cli, monkeypatch):
    monkeypatch.setattr(vision, "clasificar_foto", lambda d, m: ("NO_SE_VE", ""))
    j = cli.post("/api/v1/solicitudes", json={"contacto": "u1", "texto": "cosa rara"}).get_json()
    f = cli.post(f"/api/v1/solicitudes/{j['codigo']}/foto", content_type="multipart/form-data",
                 data=multipart(foto=foto())).get_json()
    assert f["foto_ilegible"] and f["necesita_foto"] and f["estado"] == "esperando_foto"


def test_validaciones(cli):
    assert cli.post("/api/v1/solicitudes", json={"texto": "botella"}).status_code == 400      # sin contacto
    assert cli.post("/api/v1/solicitudes", json={"contacto": "u1"}).status_code == 400        # sin texto
    assert cli.post("/api/v1/solicitudes", content_type="multipart/form-data",
                    data=multipart(contacto="u1")).status_code == 400                          # nada que clasificar
    malo = cli.post("/api/v1/solicitudes", content_type="multipart/form-data",
                    data=multipart(contacto="u1", foto=foto("a.pdf", "application/pdf")))
    assert malo.status_code == 400
    assert cli.post("/api/v1/solicitudes/RES-0-1/foto", content_type="multipart/form-data",
                    data=multipart(foto=foto())).status_code == 404


def test_foto_demasiado_grande(cli, monkeypatch):
    monkeypatch.setenv("MAX_FOTO_MB", "0.0001")
    r = cli.post("/api/v1/solicitudes", content_type="multipart/form-data",
                 data=multipart(contacto="u1", foto=foto(datos=b"x" * 5000)))
    assert r.status_code == 400


def test_fallo_de_la_ia_devuelve_502_y_deja_pendiente(cli, monkeypatch):
    def cae(d, m):
        raise RuntimeError("API caída")
    monkeypatch.setattr(vision, "clasificar_foto", cae)
    j = cli.post("/api/v1/solicitudes", json={"contacto": "u1", "texto": "cosa rara"}).get_json()
    r = cli.post(f"/api/v1/solicitudes/{j['codigo']}/foto", content_type="multipart/form-data",
                 data=multipart(foto=foto()))
    assert r.status_code == 502
    assert cli.get(f"/api/v1/solicitudes/{j['codigo']}").get_json()["estado"] == "esperando_foto"


def test_consultar_y_listar(cli):
    a = cli.post("/api/v1/solicitudes", json={"contacto": "u1", "texto": "botella de plástico"}).get_json()
    cli.post("/api/v1/solicitudes", json={"contacto": "u2", "texto": "cáscara de banano"})
    assert cli.get(f"/api/v1/solicitudes/{a['codigo']}").get_json()["categoria"] == "RECICLABLE"
    assert cli.get("/api/v1/solicitudes/RES-0-1").status_code == 404
    assert len(cli.get("/api/v1/solicitudes").get_json()) == 2
    solo_u1 = cli.get("/api/v1/solicitudes?contacto=u1").get_json()
    assert [s["contacto"] for s in solo_u1] == ["u1"]
    assert cli.get("/api/v1/solicitudes?limite=abc").status_code == 400


def test_api_key(cli, monkeypatch):
    monkeypatch.setenv("API_KEY", "secreta")
    assert cli.get("/api/v1/solicitudes").status_code == 401
    assert cli.get("/api/v1/solicitudes", headers={"X-API-Key": "mala"}).status_code == 401
    assert cli.get("/api/v1/solicitudes", headers={"X-API-Key": "secreta"}).status_code == 200
    assert cli.get("/health").status_code == 200  # /health y /webhook no usan la API key


def test_cors(cli, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://miweb.com")
    ok = cli.get("/api/v1/solicitudes", headers={"Origin": "https://miweb.com"})
    assert ok.headers["Access-Control-Allow-Origin"] == "https://miweb.com"
    otro = cli.get("/api/v1/solicitudes", headers={"Origin": "https://malo.com"})
    assert "Access-Control-Allow-Origin" not in otro.headers
    pre = cli.options("/api/v1/solicitudes", headers={"Origin": "https://miweb.com"})
    assert pre.status_code == 204


def test_whatsapp_y_api_comparten_solicitudes(cli):
    """Lo que entra por WhatsApp se puede consultar desde la app/web con el mismo código."""
    import bot
    enviados = []
    bot.procesar({"id": "1", "from_me": False, "type": "text", "chat_id": "573001@s.whatsapp.net",
                  "text": {"body": "botella de plástico"}},
                 lambda d, t: enviados.append(t), None, None)
    codigo = enviados[0].split("*")[1]
    j = cli.get(f"/api/v1/solicitudes/{codigo}").get_json()
    assert j["canal"] == "whatsapp" and j["contacto"] == "573001" and j["categoria"] == "RECICLABLE"

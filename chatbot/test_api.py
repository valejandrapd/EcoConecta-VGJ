import io

import pytest

import app as servidor
import core
import db
import notificar
import vision


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    db.iniciar()
    db.vaciar()
    for v in ("API_KEY", "CORS_ORIGINS", "BACKEND_URL", "PUNTOS_BASE", "PUNTOS_POR_KG"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(vision, "clasificar_foto", lambda datos, mime: ("RECICLABLE", "lata"))
    avisos = []
    monkeypatch.setattr(notificar.whapi, "enviar_texto", lambda d, t: avisos.append((d, t)))
    return avisos


@pytest.fixture
def avisos(entorno):
    return entorno


@pytest.fixture
def cli():
    return servidor.app.test_client()


def datos(**extra):
    base = {"contacto": "573001", "canal": "whatsapp", "generador": "negocio", "categoria": "ORGANICO",
            "direccion": "Calle 1 #2-3", "disponibilidad": "mañanas"}
    base.update(extra)
    return base


def crear(cli, **extra):
    r = cli.post("/api/v1/solicitudes", json=datos(**extra))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


# ---- clasificar
def test_clasificar_texto_y_foto(cli):
    assert cli.post("/api/v1/clasificar", json={"texto": "cáscara de banano"}).get_json()["categoria"] == "ORGANICO"
    dudoso = cli.post("/api/v1/clasificar", json={"texto": "esto de aquí"}).get_json()
    assert dudoso["necesita_foto"] and dudoso["categoria"] is None
    r = cli.post("/api/v1/clasificar", content_type="multipart/form-data",
                 data={"foto": (io.BytesIO(b"\xff\xd8x"), "r.jpg", "image/jpeg")}).get_json()
    assert r["categoria"] == "RECICLABLE" and r["metodo"] == "foto" and r["objeto"] == "lata"


def test_clasificar_validaciones_y_fallo_de_ia(cli, monkeypatch):
    assert cli.post("/api/v1/clasificar", json={}).status_code == 400
    pdf = {"foto": (io.BytesIO(b"x"), "a.pdf", "application/pdf")}
    assert cli.post("/api/v1/clasificar", content_type="multipart/form-data", data=pdf).status_code == 400
    monkeypatch.setenv("MAX_FOTO_MB", "0.0001")
    grande = {"foto": (io.BytesIO(b"x" * 5000), "a.jpg", "image/jpeg")}
    assert cli.post("/api/v1/clasificar", content_type="multipart/form-data", data=grande).status_code == 400
    monkeypatch.delenv("MAX_FOTO_MB")

    def cae(d, m):
        raise RuntimeError("API caída")
    monkeypatch.setattr(vision, "clasificar_foto", cae)
    ok = {"foto": (io.BytesIO(b"x"), "a.jpg", "image/jpeg")}
    assert cli.post("/api/v1/clasificar", content_type="multipart/form-data", data=ok).status_code == 502


# ---- solicitudes: RN-01, RN-04, RN-07
def test_rn01_cada_residuo_va_a_su_colectivo(cli):
    assert crear(cli, categoria="ORGANICO")["flujo"] == "huerteros"
    assert crear(cli, categoria="reciclable")["flujo"] == "recicladores"


def test_solicitud_exige_los_datos_minimos(cli):
    for falta in ("contacto", "direccion", "generador", "categoria", "disponibilidad"):
        d = datos()
        d.pop(falta)
        assert cli.post("/api/v1/solicitudes", json=d).status_code == 400, falta
    assert cli.post("/api/v1/solicitudes", json=datos(categoria="OTRO")).status_code == 400
    assert cli.post("/api/v1/solicitudes", json=datos(generador="alien")).status_code == 400


def test_confirmacion_de_recepcion_por_whatsapp(cli, avisos):
    s = crear(cli)
    assert avisos[0][0] == "573001" and s["codigo"] in avisos[0][1] and "huerteros" in avisos[0][1]
    crear(cli, canal="web")  # canales distintos de WhatsApp no reciben aviso
    assert len(avisos) == 1


def test_rn07_solo_el_dueno_ve_su_solicitud_y_listados_filtrados(cli):
    s = crear(cli)
    crear(cli, contacto="573002", categoria="RECICLABLE")
    assert cli.get(f"/api/v1/solicitudes/{s['codigo']}?contacto=573001").status_code == 200
    assert cli.get(f"/api/v1/solicitudes/{s['codigo']}?contacto=573999").status_code == 404
    assert cli.get("/api/v1/solicitudes/RES-0-1").status_code == 404
    assert len(cli.get("/api/v1/solicitudes").get_json()) == 2
    assert len(cli.get("/api/v1/solicitudes?contacto=573001").get_json()) == 1
    assert cli.get("/api/v1/solicitudes?flujo=recicladores").get_json()[0]["contacto"] == "573002"
    assert cli.get("/api/v1/solicitudes?estado=programada").get_json() == []
    assert cli.get("/api/v1/solicitudes?limite=abc").status_code == 400


# ---- ciclo completo: asignar -> programar -> recolectar (RN-02, RN-03, RN-04, RN-05, RN-06)
def test_ciclo_completo_con_avisos_historial_y_puntos(cli, avisos):
    s = crear(cli)
    c = s["codigo"]
    assert cli.post(f"/api/v1/solicitudes/{c}/asignar", json={"coordinador": "Coord Huerteros", "recolector": "Ana"}).get_json()["estado"] == "asignada"
    p = cli.post(f"/api/v1/solicitudes/{c}/programar", json={"dia": "martes 24 nov", "hora": "8:00 a. m."}).get_json()
    assert p["estado"] == "programada" and p["programacion"]["recolector"] == "Ana"
    assert any("programada" in t and "martes 24 nov" in t and "Ana" in t for _, t in avisos)
    r = cli.post(f"/api/v1/solicitudes/{c}/recolectar", json={"cantidad_kg": 5}).get_json()
    assert r["estado"] == "recolectada" and r["puntos"] == 20  # 10 base + 2 por kg (demostración)
    assert any("20 puntos" in t for _, t in avisos)
    assert [h["estado"] for h in r["historial"]] == ["recibida", "asignada", "programada", "recolectada"]
    assert cli.get("/api/v1/puntos/573001").get_json()["puntos"] == 20


def test_rn02_no_se_programa_sin_dia_hora_y_persona(cli):
    c = crear(cli)["codigo"]
    for cuerpo in ({}, {"dia": "lunes"}, {"dia": "lunes", "hora": "9:00"}):  # sin recolector asignado
        assert cli.post(f"/api/v1/solicitudes/{c}/programar", json=cuerpo).status_code == 400
    ok = cli.post(f"/api/v1/solicitudes/{c}/programar", json={"dia": "lunes", "hora": "9:00", "recolector": "Luis"})
    assert ok.get_json()["estado"] == "programada"


def test_rn05_puntos_solo_despues_de_registrar_la_recoleccion(cli):
    c = crear(cli)["codigo"]
    assert cli.get("/api/v1/puntos/573001").get_json()["puntos"] == 0
    assert cli.post(f"/api/v1/solicitudes/{c}/recolectar", json={"cantidad_kg": 3}).status_code == 409  # no programada
    assert cli.get("/api/v1/puntos/573001").get_json()["puntos"] == 0


def test_rn06_regla_de_puntos_parametrizable(cli, monkeypatch):
    monkeypatch.setenv("PUNTOS_BASE", "0")
    monkeypatch.setenv("PUNTOS_POR_KG", "5")
    c = crear(cli)["codigo"]
    cli.post(f"/api/v1/solicitudes/{c}/programar", json={"dia": "lunes", "hora": "9", "recolector": "Luis"})
    assert cli.post(f"/api/v1/solicitudes/{c}/recolectar", json={"cantidad_kg": 2}).get_json()["puntos"] == 10
    assert cli.post(f"/api/v1/solicitudes/{c}/recolectar", json={"cantidad_kg": 2}).status_code == 409  # ya cerrada


def test_cancelar_y_no_reabrir(cli, avisos):
    c = crear(cli)["codigo"]
    r = cli.post(f"/api/v1/solicitudes/{c}/cancelar", json={"motivo": "ya no la necesito"}).get_json()
    assert r["estado"] == "cancelada" and "cancelada" in avisos[-1][1]
    assert cli.post(f"/api/v1/solicitudes/{c}/programar", json={"dia": "x", "hora": "y", "recolector": "z"}).status_code == 409
    assert cli.get("/api/v1/puntos/573001").get_json()["puntos"] == 0


def test_cantidad_invalida(cli):
    c = crear(cli)["codigo"]
    cli.post(f"/api/v1/solicitudes/{c}/programar", json={"dia": "lunes", "hora": "9", "recolector": "Luis"})
    assert cli.post(f"/api/v1/solicitudes/{c}/recolectar", json={"cantidad_kg": "mucho"}).status_code == 400
    assert cli.post(f"/api/v1/solicitudes/{c}/recolectar", json={"cantidad_kg": -1}).status_code == 400


# ---- notificar (lo usa el backend real) y fallos de envío
def test_notificar_avisa_del_estado_actual(cli, avisos):
    c = crear(cli)["codigo"]
    avisos.clear()
    assert cli.post("/api/v1/notificar", json={"codigo": c}).get_json()["enviado"] is True
    assert c in avisos[0][1]
    assert cli.post("/api/v1/notificar", json={}).status_code == 400


def test_si_falla_whatsapp_el_cambio_de_estado_se_conserva(cli, monkeypatch):
    def cae(d, t):
        raise RuntimeError("Whapi caído")
    monkeypatch.setattr(notificar.whapi, "enviar_texto", cae)
    s = crear(cli)
    assert core.consultar(s["codigo"])["estado"] == "recibida"


# ---- seguridad
def test_api_key(cli, monkeypatch):
    monkeypatch.setenv("API_KEY", "secreta")
    assert cli.get("/api/v1/solicitudes").status_code == 401
    assert cli.get("/api/v1/solicitudes", headers={"X-API-Key": "mala"}).status_code == 401
    assert cli.get("/api/v1/solicitudes", headers={"X-API-Key": "secreta"}).status_code == 200
    assert cli.get("/health").status_code == 200


def test_cors(cli, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://miweb.com")
    ok = cli.get("/api/v1/solicitudes", headers={"Origin": "https://miweb.com"})
    assert ok.headers["Access-Control-Allow-Origin"] == "https://miweb.com"
    assert "Access-Control-Allow-Origin" not in cli.get("/api/v1/solicitudes", headers={"Origin": "https://malo.com"}).headers
    pre = cli.options("/api/v1/solicitudes", headers={"Origin": "https://miweb.com"})
    assert pre.status_code in (200, 204) and pre.headers["Access-Control-Allow-Origin"] == "https://miweb.com"


# ---- webhook
def test_webhook_ignora_mensajes_repetidos(cli, monkeypatch):
    recibidos = []
    monkeypatch.setattr(servidor, "_atender", lambda m: recibidos.append(m["id"]))
    msg = {"id": "abc-1", "from_me": False, "type": "text", "chat_id": "573@s.whatsapp.net", "text": {"body": "hola"}}
    for _ in range(2):
        assert cli.post("/webhook", json={"messages": [msg]}).status_code == 200
    import time
    time.sleep(0.2)
    assert recibidos == ["abc-1"]

"""Escenario mínimo de demostración del reto (sección 11) y reglas RN-01 a RN-08 vía API."""
from sqlalchemy import select

from app.db import sesion
from app.models import HistorialSolicitud

from .conftest import ANA, BETO, mensaje, publicar, usuario

CLAVE = {"X-Service-Key": "clave-servicio-prueba"}


def h(u):
    return {**CLAVE, "X-Usuario-Id": str(u.id)}


def test_escenario_minimo_de_demostracion(client, wa):
    ana = usuario(tel=ANA)  # unidad productiva
    beto = usuario(tel=BETO)
    c_org, c_rec = usuario("coordinador_huerteros"), usuario("coordinador_recicladores")
    carlos = usuario("huertero")

    # 1. La unidad productiva registra una solicitud de orgánicos
    r = client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico", "disponibilidad": "Mañanas",
                                                              "observaciones": "2 baldes"})
    assert r.status_code == 201, r.text
    org = r.json()
    assert org["codigo"].startswith("ORG-") and org["tipo_generador"] == "unidad_productiva"

    # 2. Llega SOLO a la bandeja del coordinador de huerteros (RN-01), que la revisa y asigna
    assert [x["codigo"] for x in client.get("/api/bandeja", headers=h(c_org)).json()["solicitudes"]] == [org["codigo"]]
    assert client.get("/api/bandeja", headers=h(c_rec)).json()["solicitudes"] == []
    assert client.post(f"/api/solicitudes/{org['codigo']}/revisar", headers=h(c_org)).json()["estado"] == "en_revision"
    r = client.post(f"/api/solicitudes/{org['codigo']}/asignar", headers=h(c_org), json={"recolector_id": carlos.id})
    assert r.json()["estado"] == "asignada" and r.json()["recolector"] == "Carlos Ruiz"

    # 3. Se programa día, hora y persona, y se comunica al usuario
    r = client.post(f"/api/solicitudes/{org['codigo']}/programar", headers=h(c_org),
                    json={"fecha": "2026-11-21", "hora": "09:00"})
    assert r.json()["estado"] == "programada"
    avisos = [e for e in wa.enviados if e[1] == ANA and (e[0] == "plantilla" and e[2] == "solicitud_programada")]
    assert avisos and avisos[0][3] == [org["codigo"], "21/11/2026", "09:00", "Carlos"]

    # 4. El huertero registra la recolección: estado y puntos (RN-05/RN-06)
    assert [x["codigo"] for x in client.get("/api/asignaciones", headers=h(carlos)).json()] == [org["codigo"]]
    r = client.post(f"/api/solicitudes/{org['codigo']}/recoleccion", headers=h(carlos), json={"cantidad_kg": "4.5"})
    assert r.json()["estado"] == "recolectada" and r.json()["puntos"] == 5 + 9  # base 5 + 4.5 kg x 2
    assert client.get("/api/mis-solicitudes", headers=h(ana)).json()["puntos"] == 14

    # RN-04: historial completo
    hist = client.get(f"/api/solicitudes/{org['codigo']}/historial", headers=h(ana)).json()
    assert [x["a"] for x in hist] == ["recibida", "en_revision", "asignada", "programada", "recolectada"]

    # 5. Un segundo usuario pide reciclables: va al coordinador de recicladores
    r = client.post("/api/solicitudes", headers=h(beto), json={"flujo": "reciclable"})
    rec = r.json()["codigo"]
    assert rec.startswith("REC-")
    assert [x["codigo"] for x in client.get("/api/bandeja", headers=h(c_rec)).json()["solicitudes"]] == [rec]
    assert rec not in [x["codigo"] for x in client.get("/api/bandeja", headers=h(c_org)).json()["solicitudes"]]

    # El estado también se consulta por WhatsApp
    publicar(client, mensaje(ANA, texto=org["codigo"]))
    assert "Recolectada" in wa.textos_a(ANA)[-1] and "Puntos ganados: 14" in wa.textos_a(ANA)[-1]


def _sol(client, dueno, flujo="organico"):
    return client.post("/api/solicitudes", headers=h(dueno), json={"flujo": flujo}).json()["codigo"]


def test_rn02_no_se_programa_sin_persona(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    r = client.post(f"/api/solicitudes/{cod}/programar", headers=h(usuario("coordinador_huerteros")),
                    json={"fecha": "2026-11-21", "hora": "09:00"})
    assert r.status_code == 400 and "persona encargada" in r.json()["detail"]


def test_rn01_no_se_asigna_recolector_de_otro_flujo(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(usuario("coordinador_huerteros")),
                    json={"recolector_id": usuario("reciclador").id})
    assert r.status_code == 400


def test_rn01_coordinador_ajeno_no_puede_asignar(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(usuario("coordinador_recicladores")),
                    json={"recolector_id": usuario("huertero").id})
    assert r.status_code == 403


def test_rn05_sin_recoleccion_no_hay_puntos(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    r = client.post(f"/api/solicitudes/{cod}/recoleccion", headers=h(usuario("coordinador_huerteros")),
                    json={"cantidad_kg": "3"})
    assert r.status_code == 400
    assert client.get("/api/mis-solicitudes", headers=h(usuario(tel=ANA))).json()["puntos"] == 0


def test_rn07_contacto_solo_para_quien_atiende(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    assert "contacto" in client.get(f"/api/solicitudes/{cod}", headers=h(usuario("coordinador_huerteros"))).json()
    # Otro solicitante y el coordinador de otro flujo no la ven
    assert client.get(f"/api/solicitudes/{cod}", headers=h(usuario(tel=BETO))).status_code == 404
    assert client.get(f"/api/solicitudes/{cod}", headers=h(usuario("coordinador_recicladores"))).status_code == 404
    # El huertero no asignado tampoco ve el contacto
    assert client.get(f"/api/solicitudes/{cod}", headers=h(usuario("huertero"))).status_code == 404


def test_rn08_usuario_fuera_del_piloto(client, wa):
    dora = usuario(tel="573005550000")
    r = client.post("/api/solicitudes", headers=h(dora), json={"flujo": "organico"})
    assert r.status_code == 403
    publicar(client, mensaje("573005550000", texto="3"))
    assert "piloto" in wa.textos_a("573005550000")[0]


def test_sin_clave_de_servicio(client):
    assert client.get("/api/bandeja", headers={"X-Usuario-Id": "1"}).status_code == 401


def test_cancelar_queda_en_historial(client, wa):
    ana = usuario(tel=ANA)
    cod = _sol(client, ana)
    assert client.post(f"/api/solicitudes/{cod}/cancelar", headers=h(ana), json={"motivo": "ya no"}).json()["estado"] == "cancelada"
    with sesion() as s:
        assert s.scalar(select(HistorialSolicitud.estado_nuevo).order_by(HistorialSolicitud.id.desc())) == "cancelada"

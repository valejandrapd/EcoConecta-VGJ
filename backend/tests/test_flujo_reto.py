"""Escenario mínimo de demostración del reto (sección 11) y reglas RN-01 a RN-08 vía API."""
from datetime import date

from sqlalchemy import select

from app.db import sesion
from app.models import HistorialSolicitud

from .conftest import ANA, BETO, mensaje, personal, proximo, publicar, usuario

CLAVE = {"X-Service-Key": "clave-servicio-prueba"}


def h(u):
    return {**CLAVE, "X-Usuario-Id": str(u.id)}


def test_escenario_minimo_de_demostracion(client, wa):
    ana = usuario(tel=ANA)  # unidad productiva
    beto = usuario(tel=BETO)
    c_org, c_rec = usuario("coordinador_huerta"), usuario("coordinador_reciclaje")
    rosa = personal("Rosa")

    # 1. La unidad productiva registra una solicitud de orgánicos
    r = client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico", "dias": ["lun", "jue"],
                                                              "hora_desde": "08:00", "hora_hasta": "11:00",
                                                              "observaciones": "2 baldes"})
    assert r.status_code == 201, r.text
    org = r.json()
    assert org["codigo"].startswith("ORG-") and org["tipo_generador"] == "unidad_productiva"

    # 2. Llega SOLO a la bandeja de la coordinación de huerta (RN-01), que la revisa y asigna un reciclador
    assert [x["codigo"] for x in client.get("/api/bandeja", headers=h(c_org)).json()["solicitudes"]] == [org["codigo"]]
    assert client.get("/api/bandeja", headers=h(c_rec)).json()["solicitudes"] == []
    assert client.post(f"/api/solicitudes/{org['codigo']}/revisar", headers=h(c_org)).json()["estado"] == "en_revision"
    # Solo aparece Rosa: es de la zona de Ana y cruza lunes/jueves de 8 a 11 (Pedro es de la zona pero solo sábados)
    ops = client.get(f"/api/solicitudes/{org['codigo']}/opciones-asignacion", headers=h(c_org)).json()
    assert [(o["nombre"], o["dias"], o["desde"], o["hasta"]) for o in ops] == [
        ("Rosa Martínez", ["lun", "jue"], "08:00:00", "11:00:00")]
    r = client.post(f"/api/solicitudes/{org['codigo']}/asignar", headers=h(c_org), json={"reciclador_id": rosa.id})
    assert r.json()["estado"] == "asignada" and r.json()["reciclador"] == "Rosa Martínez"

    # 3. Se programa día, hora y persona, y se comunica al usuario
    lunes = proximo("lun")
    r = client.post(f"/api/solicitudes/{org['codigo']}/programar", headers=h(c_org),
                    json={"fecha": str(lunes), "hora": "09:00"})
    assert r.json()["estado"] == "programada", r.text
    avisos = [e for e in wa.enviados if e[1] == ANA and (e[0] == "plantilla" and e[2] == "solicitud_programada")]
    assert avisos and avisos[0][3] == [org["codigo"], f"{lunes:%d/%m/%Y}", "09:00", "Rosa"]

    # 4. El reciclador entrega y la coordinación registra la recolección: estado y puntos (RN-05/RN-06)
    r = client.post(f"/api/solicitudes/{org['codigo']}/recoleccion", headers=h(c_org), json={"cantidad_kg": "4.5"})
    assert r.json()["estado"] == "recolectada" and r.json()["puntos"] == 5 + 9  # base 5 + 4.5 kg x 2
    assert client.get("/api/mis-solicitudes", headers=h(ana)).json()["puntos"] == 14

    # RN-04: historial completo
    hist = client.get(f"/api/solicitudes/{org['codigo']}/historial", headers=h(ana)).json()
    assert [x["a"] for x in hist] == ["recibida", "en_revision", "asignada", "programada", "recolectada"]

    # 5. Un segundo usuario pide reciclables: va a la coordinación de reciclaje
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
    r = client.post(f"/api/solicitudes/{cod}/programar", headers=h(usuario("coordinador_huerta")),
                    json={"fecha": str(proximo("lun")), "hora": "09:00"})
    assert r.status_code == 400 and "reciclador" in r.json()["detail"]


def test_asignacion_respeta_zona_y_horarios(client, wa):
    """Usuario disponible lunes y martes de 1 a 5 p. m.: ni Rosa (mañanas) ni Pedro (sábados) sirven;
    Luis es de otra zona. Ninguno aparece y el backend rechaza asignarlos."""
    ana, coord = usuario(tel=ANA), usuario("coordinador_huerta")
    cod = client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico", "dias": ["lun", "mar"],
                                                               "hora_desde": "13:00", "hora_hasta": "17:00"}).json()["codigo"]
    assert client.get(f"/api/solicitudes/{cod}/opciones-asignacion", headers=h(coord)).json() == []
    for nombre in ("Rosa", "Pedro", "Luis"):
        r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(coord), json={"reciclador_id": personal(nombre).id})
        assert r.status_code == 400 and "zona" in r.json()["detail"], nombre
    # Los voluntarios de huerta no recolectan
    r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(coord), json={"reciclador_id": personal("Carlos").id})
    assert r.status_code == 400 and "recicladores" in r.json()["detail"]


def test_programacion_solo_dentro_de_la_ventana(client, wa):
    ana, coord, rosa = usuario(tel=ANA), usuario("coordinador_huerta"), personal("Rosa")
    cod = client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico", "dias": ["mar", "sab"],
                                                               "hora_desde": "09:00", "hora_hasta": "15:00"}).json()["codigo"]
    ops = {o["nombre"]: o for o in client.get(f"/api/solicitudes/{cod}/opciones-asignacion", headers=h(coord)).json()}
    # Pedro solo cruza el sábado de 1 a 3 p. m.
    assert ops["Pedro Sáenz"]["dias"] == ["sab"] and ops["Pedro Sáenz"]["desde"] == "13:00:00"
    # Rosa no trabaja sábados y termina a las 12: queda martes de 9 a 12
    op = ops["Rosa Martínez"]
    assert op["dias"] == ["mar"] and (op["desde"], op["hasta"]) == ("09:00:00", "12:00:00")
    assert all(date.fromisoformat(f).weekday() == 1 for f in op["fechas"])
    malo = [("sab", "10:00"), ("mar", "08:00"), ("mar", "12:00"), ("mar", "13:00")]
    for dia, hora in malo:
        r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(coord),
                        json={"reciclador_id": rosa.id, "fecha": str(proximo(dia)), "hora": hora})
        assert r.status_code == 400, (dia, hora)
    # Asignar y programar en un paso
    r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(coord),
                    json={"reciclador_id": rosa.id, "fecha": op["fechas"][0], "hora": "11:30"})
    assert r.status_code == 200 and r.json()["estado"] == "programada", r.text


def test_rn01_coordinador_ajeno_no_puede_asignar(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(usuario("coordinador_reciclaje")),
                    json={"reciclador_id": personal("Rosa").id})
    assert r.status_code == 403
    assert client.get(f"/api/solicitudes/{cod}/opciones-asignacion",
                      headers=h(usuario("coordinador_reciclaje"))).status_code == 403


def test_rn05_sin_recoleccion_no_hay_puntos(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    r = client.post(f"/api/solicitudes/{cod}/recoleccion", headers=h(usuario("coordinador_huerta")),
                    json={"cantidad_kg": "3"})
    assert r.status_code == 400
    assert client.get("/api/mis-solicitudes", headers=h(usuario(tel=ANA))).json()["puntos"] == 0


def test_rn07_contacto_solo_para_quien_atiende(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    assert "contacto" in client.get(f"/api/solicitudes/{cod}", headers=h(usuario("coordinador_huerta"))).json()
    # Otro solicitante y el coordinador de otro flujo no la ven
    assert client.get(f"/api/solicitudes/{cod}", headers=h(usuario(tel=BETO))).status_code == 404
    assert client.get(f"/api/solicitudes/{cod}", headers=h(usuario("coordinador_reciclaje"))).status_code == 404


def test_rn08_usuario_fuera_del_piloto(client, wa):
    dora = usuario(tel="573005550000")
    r = client.post("/api/solicitudes", headers=h(dora), json={"flujo": "organico"})
    assert r.status_code == 403
    publicar(client, mensaje("573005550000", texto="3"))
    assert "piloto" in wa.textos_a("573005550000")[0]


def test_sin_clave_de_servicio(client):
    assert client.get("/api/bandeja", headers={"X-Usuario-Id": "1"}).status_code == 401


def test_solo_el_usuario_cancela(client, wa):
    cod = _sol(client, usuario(tel=ANA))
    for otro in (usuario("coordinador_huerta"), usuario(tel=BETO)):
        assert client.post(f"/api/solicitudes/{cod}/cancelar", headers=h(otro), json={}).status_code in (403, 404)


def test_coordinacion_cambia_la_fecha(client, wa):
    ana, coord, rosa = usuario(tel=ANA), usuario("coordinador_huerta"), personal("Rosa")
    cod = client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico", "dias": ["lun", "mie"],
                                                               "hora_desde": "08:00", "hora_hasta": "11:00"}).json()["codigo"]
    client.post(f"/api/solicitudes/{cod}/asignar", headers=h(coord),
                json={"reciclador_id": rosa.id, "fecha": str(proximo("lun")), "hora": "09:00"})
    # Nueva fecha: sigue limitada a lo que eligió el usuario y al horario de Rosa
    r = client.post(f"/api/solicitudes/{cod}/programar", headers=h(coord), json={"fecha": str(proximo("mar")), "hora": "09:00"})
    assert r.status_code == 400
    r = client.post(f"/api/solicitudes/{cod}/programar", headers=h(coord), json={"fecha": str(proximo("mie")), "hora": "10:30"})
    assert r.status_code == 200 and r.json()["fecha_programada"] == str(proximo("mie"))
    assert r.json()["reciclador"] == "Rosa Martínez"
    avisos = [e for e in wa.enviados if e[1] == ANA and e[0] == "plantilla" and e[2] == "solicitud_programada"]
    assert len(avisos) == 2  # el usuario recibe el aviso del cambio


def test_cancelar_queda_en_historial(client, wa):
    ana = usuario(tel=ANA)
    cod = _sol(client, ana)
    assert client.post(f"/api/solicitudes/{cod}/cancelar", headers=h(ana), json={"motivo": "ya no"}).json()["estado"] == "cancelada"
    with sesion() as s:
        assert s.scalar(select(HistorialSolicitud.estado_nuevo).order_by(HistorialSolicitud.id.desc())) == "cancelada"

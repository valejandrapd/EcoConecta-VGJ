"""Mapa de zonas y ficha del reciclador: separación de flujos (RN-01), privacidad (RN-07) y kilos tras el cierre (RN-05)."""
from .conftest import ANA, BETO, personal, proximo, usuario

CLAVE = {"X-Service-Key": "clave-servicio-prueba"}


def h(u):
    return {**CLAVE, "X-Usuario-Id": str(u.id)}


def _zona(datos, nombre):
    return next(z for z in datos["zonas"] if z["nombre"] == nombre)


def _organica_programada(client):
    """Ana (Sector 1) pide orgánicos; la coordinación de huerta asigna a Rosa y programa."""
    ana, c_org = usuario(tel=ANA), usuario("coordinador_huerta")
    r = client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico", "dias": ["lun", "jue"],
                                                              "hora_desde": "08:00", "hora_hasta": "11:00"})
    codigo = r.json()["codigo"]
    client.post(f"/api/solicitudes/{codigo}/asignar", headers=h(c_org), json={"reciclador_id": personal("Rosa").id})
    client.post(f"/api/solicitudes/{codigo}/programar", headers=h(c_org),
                json={"fecha": str(proximo("lun")), "hora": "09:00"})
    return codigo


def test_solo_la_coordinacion_y_el_administrador_ven_el_mapa(client):
    ana = usuario(tel=ANA)
    assert client.get("/api/mapa/zonas", headers=h(ana)).status_code == 403
    assert client.get(f"/api/personal/{personal('Rosa').id}/agenda", headers=h(ana)).status_code == 403
    for rol in ("coordinador_huerta", "coordinador_reciclaje", "administrador"):
        assert client.get("/api/mapa/zonas", headers=h(usuario(rol))).status_code == 200


def test_recicladores_por_zona_sin_voluntarios_de_huerta(client):
    datos = client.get("/api/mapa/zonas", headers=h(usuario("coordinador_reciclaje"))).json()
    assert [z["nombre"] for z in datos["zonas"]] == [f"Sector {i}" for i in range(1, 5)]
    assert {r["nombre"] for r in _zona(datos, "Sector 1")["recicladores"]} == {"Rosa", "Pedro"}
    assert [r["nombre"] for r in _zona(datos, "Sector 2")["recicladores"]] == ["Luis"]
    todos = [r["nombre"] for z in datos["zonas"] for r in z["recicladores"]]
    assert "Carlos" not in todos  # los voluntarios de huerta no son recicladores de zona


def test_las_metricas_respetan_la_separacion_de_flujos(client):
    ana, beto = usuario(tel=ANA), usuario(tel=BETO)
    client.post("/api/solicitudes", headers=h(ana), json={"flujo": "organico"})        # Sector 1, orgánico
    client.post("/api/solicitudes", headers=h(beto), json={"flujo": "reciclable"})     # Sector 2, reciclable

    def solicitudes(rol):
        d = client.get("/api/mapa/zonas", headers=h(usuario(rol))).json()
        return {z["nombre"]: z["metricas"]["solicitudes_30d"] for z in d["zonas"]}

    assert solicitudes("coordinador_huerta") == {"Sector 1": 1, "Sector 2": 0, "Sector 3": 0, "Sector 4": 0}
    assert solicitudes("coordinador_reciclaje") == {"Sector 1": 0, "Sector 2": 1, "Sector 3": 0, "Sector 4": 0}
    assert solicitudes("administrador") == {"Sector 1": 1, "Sector 2": 1, "Sector 3": 0, "Sector 4": 0}


def test_los_kilos_solo_cuentan_despues_de_registrar_la_recoleccion(client):
    c_org, c_rec = usuario("coordinador_huerta"), usuario("coordinador_reciclaje")
    codigo = _organica_programada(client)

    antes = _zona(client.get("/api/mapa/zonas", headers=h(c_org)).json(), "Sector 1")["metricas"]
    assert antes["kilos_30d"]["total"] == 0 and antes["tasa_atencion"] == 0  # RN-05: sin recolección no hay kilos

    client.post(f"/api/solicitudes/{codigo}/recoleccion", headers=h(c_org), json={"cantidad_kg": "4.5"})
    m = _zona(client.get("/api/mapa/zonas", headers=h(c_org)).json(), "Sector 1")["metricas"]
    assert m["kilos_30d"] == {"organico": 4.5, "reciclable": 0.0, "total": 4.5}
    assert m["material_principal"] == "organico" and m["tasa_atencion"] == 100 and m["usuarios_30d"] == 1
    # La coordinación de reciclaje no ve los kilos del flujo orgánico (RN-01)
    otro = _zona(client.get("/api/mapa/zonas", headers=h(c_rec)).json(), "Sector 1")["metricas"]
    assert otro["kilos_30d"]["total"] == 0 and otro["solicitudes_30d"] == 0


def test_agenda_del_reciclador_solo_con_las_solicitudes_de_su_flujo(client):
    c_org, c_rec = usuario("coordinador_huerta"), usuario("coordinador_reciclaje")
    rosa = personal("Rosa")
    codigo = _organica_programada(client)

    d = client.get(f"/api/personal/{rosa.id}/agenda", headers=h(c_org)).json()
    assert d["reciclador"]["nombre_completo"] == "Rosa Martínez" and d["reciclador"]["zona"] == "Sector 1"
    assert d["reciclador"]["dias"] == ["lun", "mar", "mie", "jue", "vie"]
    assert [s["codigo"] for s in d["solicitudes"]] == [codigo]
    assert d["solicitudes"][0]["fecha_programada"] == str(proximo("lun")) and d["solicitudes"][0]["contacto"]  # RN-07: la atiende
    # La coordinación de reciclaje no ve las solicitudes orgánicas de Rosa ni su contacto (RN-01 / RN-07)
    assert client.get(f"/api/personal/{rosa.id}/agenda", headers=h(c_rec)).json()["solicitudes"] == []


def test_la_agenda_es_solo_de_recicladores(client):
    carlos = personal("Carlos")  # voluntario de huerta
    assert client.get(f"/api/personal/{carlos.id}/agenda", headers=h(usuario("coordinador_huerta"))).status_code == 404
    assert client.get("/api/personal/9999/agenda", headers=h(usuario("coordinador_huerta"))).status_code == 404

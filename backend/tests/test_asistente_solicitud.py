"""Asistente de nueva solicitud: tamaño, días, horario, dirección etiquetada, bonificación e insignias."""
from sqlalchemy import text

from app.db import _agregar_columnas_nuevas, sesion

from .conftest import ANA, usuario

CLAVE = {"X-Service-Key": "clave-servicio-prueba"}


def h(u):
    return {**CLAVE, "X-Usuario-Id": str(u.id)}


PASOS = {"flujo": "reciclable", "tamano": "mediano", "dias": ["vie", "lun"], "hora_desde": "08:00",
         "hora_hasta": "12:00", "bonificacion": "tiendas"}


def _recolectar(client, codigo, kg):
    coord = usuario("coordinador_recicladores" if codigo.startswith("REC") else "coordinador_huerteros")
    rec = usuario("reciclador" if codigo.startswith("REC") else "huertero")
    client.post(f"/api/solicitudes/{codigo}/asignar", headers=h(coord), json={"recolector_id": rec.id})
    client.post(f"/api/solicitudes/{codigo}/programar", headers=h(coord), json={"fecha": "2026-11-21", "hora": "09:00"})
    r = client.post(f"/api/solicitudes/{codigo}/recoleccion", headers=h(rec), json={"cantidad_kg": kg})
    assert r.status_code == 200, r.text


def test_solicitud_con_todos_los_pasos(client, wa):
    ana = usuario(tel=ANA)
    r = client.post("/api/solicitudes", headers=h(ana), json=PASOS)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["tamano"] == "mediano" and s["dias_disponibles"] == ["lun", "vie"] and s["bonificacion"] == "tiendas"
    assert s["disponibilidad"] == "Lun, Vie · 08:00 a 12:00"
    assert s["contacto"]["direccion"] == "Calle 10 # 1-2" and s["contacto"]["etiqueta"] is None


def test_nueva_direccion_con_etiqueta_se_guarda(client, wa):
    ana = usuario(tel=ANA)
    r = client.post("/api/solicitudes", headers=h(ana), json={**PASOS, "direccion": "Mz 7 casa 3",
                                                              "direccion_etiqueta": "Casa mamá"})
    assert r.json()["contacto"] == {"nombre": "Ana Pérez", "telefono": "+" + ANA, "direccion": "Mz 7 casa 3",
                                    "etiqueta": "Casa mamá"}
    d = client.get("/api/mis-direcciones", headers=h(ana)).json()
    assert d == {"principal": "Calle 10 # 1-2", "guardadas": [{"etiqueta": "Casa mamá", "direccion": "Mz 7 casa 3"}]}
    # La misma etiqueta actualiza la dirección, no la duplica
    client.post("/api/solicitudes", headers=h(ana), json={**PASOS, "direccion": "Mz 7 casa 5",
                                                          "direccion_etiqueta": "Casa mamá"})
    assert client.get("/api/mis-direcciones", headers=h(ana)).json()["guardadas"] == [
        {"etiqueta": "Casa mamá", "direccion": "Mz 7 casa 5"}]


def test_validaciones_del_asistente(client):
    ana = usuario(tel=ANA)
    for malo in ({"tamano": "enorme"}, {"dias": []}, {"dias": ["lunes"]}, {"hora_desde": "12:00"},
                 {"hora_desde": "12:00", "hora_hasta": "08:00"}, {"bonificacion": "efectivo"}):
        r = client.post("/api/solicitudes", headers=h(ana), json={**PASOS, **malo})
        assert r.status_code == 400, malo


def test_insignias_crecen_con_los_puntos(client, wa):
    ana = usuario(tel=ANA)
    rec = client.post("/api/solicitudes", headers=h(ana), json=PASOS).json()["codigo"]
    org = client.post("/api/solicitudes", headers=h(ana),
                      json={**PASOS, "flujo": "organico", "bonificacion": "huerto"}).json()["codigo"]
    _recolectar(client, rec, 3)   # 5 + 3x3 = 14 puntos para tiendas
    _recolectar(client, org, 1)   # 5 + 1x2 = 7 puntos para el huerto
    d = client.get("/api/mis-solicitudes", headers=h(ana)).json()
    assert d["puntos"] == 21
    assert d["insignias"]["alcancia"] == {"puntos": 14, "nivel": 1, "nivel_maximo": 5, "paso": 10, "faltan": 6}
    assert d["insignias"]["trinitaria"] == {"puntos": 7, "nivel": 1, "nivel_maximo": 5, "paso": 5, "faltan": 3}


def test_migracion_agrega_columnas_a_base_antigua():
    with sesion() as s:
        s.execute(text("ALTER TABLE solicitudes DROP COLUMN tamano, DROP COLUMN bonificacion"))
    _agregar_columnas_nuevas()
    with sesion() as s:
        cols = set(s.scalars(text("SELECT column_name FROM information_schema.columns "
                                  "WHERE table_name = 'solicitudes'")).all())
    assert {"tamano", "bonificacion"} <= cols

"""Bandeja web de notificaciones del solicitante."""
from datetime import date, timedelta

from app import bandeja
from app.db import sesion
from app.models import DIAS_SEMANA, Solicitud, Usuario

from .conftest import ANA, BETO, personal, proximo, usuario

CLAVE = {"X-Service-Key": "clave-servicio-prueba"}


def h(u):
    return {**CLAVE, "X-Usuario-Id": str(u.id)}


def _crear(client, dueno, zona="Sector 1"):
    r = client.post("/api/solicitudes", headers=h(dueno), json={"flujo": "organico", "zona": zona})
    assert r.status_code == 201, r.text
    return r.json()["codigo"]


def _asignar(client, cod, rec, coord=None):
    coord = coord or usuario("coordinador_huerta")
    r = client.post(f"/api/solicitudes/{cod}/asignar", headers=h(coord), json={"reciclador_id": rec.id})
    assert r.status_code == 200, r.text


def _programar(client, cod, fecha, hora="09:00"):
    r = client.post(f"/api/solicitudes/{cod}/programar", headers=h(usuario("coordinador_huerta")),
                    json={"fecha": str(fecha), "hora": hora})
    assert r.status_code == 200, r.text


def _lista(client, u):
    r = client.get("/api/notificaciones", headers=h(u))
    assert r.status_code == 200, r.text
    return r.json()


def _tipos(client, u):
    return [n["tipo"] for n in _lista(client, u)]


def _vecina():
    with sesion() as s:
        v = Usuario(nombre="Vera Vecina", telefono="+573009990000", direccion="Calle 11", zona="Sector 1", piloto=True)
        s.add(v)
    return usuario(tel="573009990000")


def _dia_habil_rosa_desde(dias: int) -> date:
    d = date.today() + timedelta(days=dias)
    while DIAS_SEMANA[d.weekday()] not in ("lun", "mar", "mie", "jue", "vie"):
        d += timedelta(days=1)
    return d


def test_asignar_y_programar_avisan_al_dueno(client, wa):
    ana, rosa = usuario(tel=ANA), personal("Rosa")
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    _asignar(client, cod, rosa)  # mismo reciclador: no repite
    assert _tipos(client, ana).count("asignada") == 1
    lunes = proximo("lun")
    _programar(client, cod, lunes)
    lista = _lista(client, ana)
    prog = [n for n in lista if n["tipo"] == "programada"]
    assert len(prog) == 1 and "Rosa Martínez" in prog[0]["cuerpo"] and f"{lunes:%d/%m}" in prog[0]["cuerpo"]
    assert "9 a. m." in prog[0]["cuerpo"] and prog[0]["codigo_solicitud"] == cod
    assert client.get("/api/notificaciones/contador", headers=h(ana)).json()["no_leidas"] == 2


def test_reprogramar_oculta_el_aviso_viejo(client, wa):
    ana, rosa = usuario(tel=ANA), personal("Rosa")
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    _programar(client, cod, proximo("lun"))
    _programar(client, cod, proximo("mar"), "10:00")
    prog = [n for n in _lista(client, ana) if n["tipo"] == "programada"]
    assert len(prog) == 1 and "10 a. m." in prog[0]["cuerpo"]


def test_cancelar_oculta_recordatorios(client, wa, monkeypatch):
    ana, rosa = usuario(tel=ANA), personal("Rosa")
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    fecha = _dia_habil_rosa_desde(1)
    _programar(client, cod, fecha)
    monkeypatch.setattr(bandeja, "_hoy", lambda: fecha - timedelta(days=1))
    assert "recordatorio_manana" in _tipos(client, ana)
    assert _tipos(client, ana).count("recordatorio_manana") == 1  # no se duplica
    client.post(f"/api/solicitudes/{cod}/cancelar", headers=h(ana), json={"motivo": "x"})
    tipos = _tipos(client, ana)
    assert "recordatorio_manana" not in tipos and "programada" not in tipos


def test_recordatorio_del_mismo_dia(client, wa, monkeypatch):
    ana, rosa = usuario(tel=ANA), personal("Rosa")
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    fecha = _dia_habil_rosa_desde(1)
    _programar(client, cod, fecha)
    monkeypatch.setattr(bandeja, "_hoy", lambda: fecha)
    hoy = [n for n in _lista(client, ana) if n["tipo"] == "recordatorio_hoy"]
    assert len(hoy) == 1 and "Hoy pasan" in hoy[0]["cuerpo"]


def test_aviso_de_zona_unico_y_sin_datos_ajenos(client, wa):
    ana, beto, rosa = usuario(tel=ANA), usuario(tel=BETO), personal("Rosa")
    vera = _vecina()
    fecha = _dia_habil_rosa_desde(2)
    for hora in ("10:00", "08:00"):  # dos recogidas de Ana el mismo día en la misma zona
        cod = _crear(client, ana)
        _asignar(client, cod, rosa)
        _programar(client, cod, fecha, hora)
    zona = [n for n in _lista(client, vera) if n["tipo"] == "zona"]
    assert len(zona) == 1
    z = zona[0]
    assert z["accion"] == "nueva_solicitud" and z["codigo_solicitud"] is None
    assert "Sector 1" in z["cuerpo"] and "8 a. m." in z["cuerpo"]
    for dato in ("Ana", "Pérez", "Calle 10", "ORG-", "Rosa"):
        assert dato not in z["cuerpo"] and dato not in z["titulo"]
    assert "zona" not in _tipos(client, beto)  # otra zona
    assert "zona" not in _tipos(client, ana)   # la dueña ya tiene su aviso propio


def test_aviso_de_zona_desaparece_si_se_cancela_la_visita(client, wa):
    ana, rosa = usuario(tel=ANA), personal("Rosa")
    vera = _vecina()
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    _programar(client, cod, _dia_habil_rosa_desde(2))
    assert "zona" in _tipos(client, vera)
    client.post(f"/api/solicitudes/{cod}/cancelar", headers=h(ana), json={"motivo": "x"})
    assert "zona" not in _tipos(client, vera)


def test_respaldo_para_solicitudes_previas(client, wa):
    ana, rosa = usuario(tel=ANA), personal("Rosa")
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    _programar(client, cod, proximo("lun"))
    from sqlalchemy import delete
    from app.models import Notificacion
    with sesion() as s:
        s.execute(delete(Notificacion))
    tipos = _tipos(client, ana)
    assert "asignada" in tipos and "programada" in tipos


def test_leer_y_permisos(client, wa):
    ana, beto, rosa = usuario(tel=ANA), usuario(tel=BETO), personal("Rosa")
    cod = _crear(client, ana)
    _asignar(client, cod, rosa)
    nid = _lista(client, ana)[0]["id"]
    assert client.post(f"/api/notificaciones/{nid}/leida", headers=h(beto)).status_code == 404
    assert client.post(f"/api/notificaciones/{nid}/leida", headers=h(ana)).status_code == 200
    assert _lista(client, ana)[0]["leida"] is True
    assert client.get("/api/notificaciones/contador", headers=h(ana)).json()["no_leidas"] == 0
    assert _lista(client, usuario("coordinador_huerta")) == []
    assert client.post("/api/notificaciones/leer-todas", headers=h(ana)).status_code == 200

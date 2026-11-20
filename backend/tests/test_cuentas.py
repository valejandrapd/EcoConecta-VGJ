"""Registro, inicio de sesión, perfiles y contenidos."""
from .conftest import usuario

CLAVE = {"X-Service-Key": "clave-servicio-prueba"}


def h(u):
    return {**CLAVE, "X-Usuario-Id": str(u.id)}


REG = {"nombre": "Nuevo Hogar", "telefono": "300 777 8899", "direccion": "Mz 3 casa 1",
       "tipo_generador": "hogar", "clave": "secreta1", "acepta_tratamiento_datos": True}


def test_registro_login_y_token(client):
    r = client.post("/api/auth/registro", json=REG)
    assert r.status_code == 201
    assert r.json()["usuario"]["piloto"] is False  # RN-08: espera habilitación
    assert client.post("/api/auth/registro", json=REG).status_code == 409
    assert client.post("/api/auth/login", json={"telefono": "+573007778899", "clave": "mala"}).status_code == 401
    tok = client.post("/api/auth/login", json={"telefono": "3007778899", "clave": "secreta1"}).json()["token"]
    yo = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {tok}"}).json()
    assert yo["nombre"] == "Nuevo Hogar" and yo["rol"] == "solicitante" and yo["puntos"] == 0
    # Fuera del piloto no puede solicitar
    r = client.post("/api/solicitudes", json={"flujo": "organico"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_token_alterado(client):
    assert client.get("/api/auth/yo", headers={"Authorization": "Bearer abc.def"}).status_code == 401


def test_registro_exige_consentimiento(client):
    assert client.post("/api/auth/registro", json={**REG, "acepta_tratamiento_datos": False}).status_code == 400


def test_admin_habilita_piloto(client):
    nuevo = client.post("/api/auth/registro", json=REG).json()["usuario"]
    admin = usuario("administrador")
    assert client.patch(f"/api/usuarios/{nuevo['id']}", headers=h(admin), json={"piloto": True}).json()["piloto"]
    assert client.patch(f"/api/usuarios/{nuevo['id']}", headers=h(usuario("huertero")),
                        json={"piloto": True}).status_code == 403


def test_contenidos_crud_solo_admin(client):
    admin = usuario("administrador")
    c = {"tipo": "huerta", "titulo": "La huerta comunitaria", "cuerpo": "Abierta los sábados."}
    assert client.post("/api/contenidos", headers=h(usuario("coordinador_huerteros")), json=c).status_code == 403
    creado = client.post("/api/contenidos", headers=h(admin), json=c).json()
    assert [x["titulo"] for x in client.get("/api/contenidos").json()] == ["La huerta comunitaria"]
    client.put(f"/api/contenidos/{creado['id']}", headers=h(admin), json={**c, "activo": False})
    assert client.get("/api/contenidos").json() == []


def test_recolectores_por_flujo(client):
    r = client.get("/api/recolectores", headers=h(usuario("coordinador_recicladores"))).json()
    assert [x["rol"] for x in r] == ["reciclador"]


def test_parametros_publicos(client):
    p = client.get("/api/parametros").json()
    assert p["puntos"]["base_por_recoleccion"] == 5 and "validación" in p["puntos"]["nota"]

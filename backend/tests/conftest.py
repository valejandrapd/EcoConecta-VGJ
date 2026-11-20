"""Pruebas contra PostgreSQL real (TEST_DATABASE_URL). Sin llamadas a Meta ni a Claude: todo simulado."""
import io
import json
import os

os.environ.setdefault("DATABASE_URL", os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://eco:eco@localhost:5432/ecoconecta_test"))
os.environ.update({
    "WHATSAPP_APP_SECRET": "secreto-de-prueba",
    "WHATSAPP_VERIFY_TOKEN": "verificar-prueba",
    "SERVICE_API_KEY": "clave-servicio-prueba",
    "NOTIFICADOR": "log",
    "ANTHROPIC_API_KEY": "",
    "LIMITE_MENSAJES_DIA": "5",
    "AUTH_SECRET": "secreto-de-firma-de-pruebas-0123",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.db import Base, crear_tablas, engine, sesion  # noqa: E402
from app.main import app  # noqa: E402
from datetime import date, time, timedelta  # noqa: E402

from app.models import DIAS_SEMANA, PersonalCampo, Usuario  # noqa: E402
from app.whatsapp import cliente as wa_cliente  # noqa: E402
from app.whatsapp.firma import firmar  # noqa: E402

SECRETO = "secreto-de-prueba"
ANA = "573001112233"     # registrada
BETO = "573004445566"    # registrado (tercero)
EXTRANO = "573009998877"  # no registrado


class ClienteFalso:
    def __init__(self):
        self.enviados = []
        self.media = b""

    def enviar_texto(self, wa_id, texto):
        self.enviados.append(("texto", wa_id, texto))
        return "wamid.out"

    def enviar_plantilla(self, wa_id, nombre, parametros):
        self.enviados.append(("plantilla", wa_id, nombre, list(parametros)))
        return "wamid.out"

    def descargar_media(self, media_id):
        return self.media

    def textos_a(self, wa_id):
        return [e[2] for e in self.enviados if e[0] == "texto" and e[1] == wa_id]


@pytest.fixture(autouse=True)
def base():
    crear_tablas()
    Base.metadata.drop_all(engine())
    crear_tablas()
    with sesion() as s:
        s.add_all([
            Usuario(nombre="Ana Pérez", telefono="+" + ANA, direccion="Calle 10 # 1-2", zona="Sector 1", piloto=True,
                    tipo_generador="unidad_productiva"),
            Usuario(nombre="Beto Gómez", telefono="+" + BETO, direccion="Carrera 5 # 9-9", zona="Sector 2",
                    piloto=True),
            Usuario(nombre="Coord Org", telefono="+573000000003", rol="coordinador_huerta"),
            Usuario(nombre="Coord Rec", telefono="+573000000004", rol="coordinador_reciclaje"),
            Usuario(nombre="Admin", telefono="+573000000007", rol="administrador"),
            Usuario(nombre="Dora Fuera", telefono="+573005550000", direccion="Mz 1", piloto=False),
            # Personal de campo sin cuenta
            PersonalCampo(tipo="reciclador", nombre="Rosa", apellido="Martínez", zona="Sector 1",
                          dias_servicio="lun,mar,mie,jue,vie", hora_desde=time(7), hora_hasta=time(12)),
            PersonalCampo(tipo="reciclador", nombre="Luis", apellido="Herrera", zona="Sector 2",
                          dias_servicio="lun,mie,vie,sab", hora_desde=time(8), hora_hasta=time(17)),
            PersonalCampo(tipo="reciclador", nombre="Pedro", apellido="Sáenz", zona="Sector 1",
                          dias_servicio="sab", hora_desde=time(13), hora_hasta=time(18)),
            PersonalCampo(tipo="voluntario_huerta", nombre="Carlos", apellido="Ruiz",
                          dias_servicio="sab,dom", hora_desde=time(7), hora_hasta=time(11)),
        ])
    yield


@pytest.fixture
def wa():
    falso = ClienteFalso()
    wa_cliente.usar_cliente(falso)
    yield falso
    wa_cliente.usar_cliente(None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


_contador = {"n": 0}


def mensaje(de, tipo="text", texto="hola", media_id="media-1", wamid=None):
    _contador["n"] += 1
    msg = {"from": de, "id": wamid or f"wamid.{_contador['n']}", "timestamp": "1700000000", "type": tipo}
    if tipo == "text":
        msg["text"] = {"body": texto}
    elif tipo == "image":
        msg["image"] = {"id": media_id, "mime_type": "image/jpeg"}
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "123"},
        "contacts": [{"wa_id": de, "profile": {"name": "Nombre"}}], "messages": [msg]}}]}]}


def publicar(client, carga, secreto=SECRETO):
    cuerpo = json.dumps(carga).encode()
    return client.post("/webhook", content=cuerpo, headers={
        "Content-Type": "application/json", "X-Hub-Signature-256": firmar(cuerpo, secreto)})


def personal(nombre):
    from sqlalchemy import select
    with sesion() as s:
        return s.scalar(select(PersonalCampo).where(PersonalCampo.nombre == nombre))


def proximo(dia: str) -> date:
    """Próxima fecha (desde mañana) que cae en ese día de la semana ('lun'...'dom')."""
    d = date.today() + timedelta(days=1)
    while DIAS_SEMANA[d.weekday()] != dia:
        d += timedelta(days=1)
    return d


def usuario(rol=None, tel=None):
    from sqlalchemy import select
    with sesion() as s:
        q = select(Usuario).where(Usuario.telefono == "+" + tel) if tel else select(Usuario).where(Usuario.rol == rol)
        return s.scalar(q)


def jpeg_con_exif(ancho=3000, alto=2000) -> bytes:
    img = Image.new("RGB", (ancho, alto), (120, 200, 80))
    exif = Image.Exif()
    exif[0x010F] = "CamaraSecreta"  # Make
    b = io.BytesIO()
    img.save(b, format="JPEG", exif=exif.tobytes())
    return b.getvalue()

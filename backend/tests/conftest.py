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
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.db import Base, crear_tablas, engine, sesion  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Usuario  # noqa: E402
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
            Usuario(nombre="Ana Pérez", telefono="+" + ANA, direccion="Calle 10 # 1-2"),
            Usuario(nombre="Beto Gómez", telefono="+" + BETO, direccion="Carrera 5 # 9-9"),
            Usuario(nombre="Carlos Ruiz", telefono="+573000000002", rol="recolector"),
            Usuario(nombre="Coord Org", telefono="+573000000003", rol="coordinador", flujo="organico"),
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


def jpeg_con_exif(ancho=3000, alto=2000) -> bytes:
    img = Image.new("RGB", (ancho, alto), (120, 200, 80))
    exif = Image.Exif()
    exif[0x010F] = "CamaraSecreta"  # Make
    b = io.BytesIO()
    img.save(b, format="JPEG", exif=exif.tobytes())
    return b.getvalue()

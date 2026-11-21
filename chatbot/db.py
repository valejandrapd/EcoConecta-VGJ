"""Almacenamiento con SQLAlchemy sobre PostgreSQL (obligatorio; no hay alternativa SQLite).

Se configura con DATABASE_URL, p. ej. postgresql://usuario:clave@localhost:5432/ecoconecta
Si no está definida o no apunta a PostgreSQL, el programa se detiene con un error claro.

Tablas:
  solicitudes    una fila por solicitud de recolección (identificador, flujo, estado, programación, puntos)
  historial      cada cambio de estado de una solicitud (RN-04 trazabilidad)
  conversaciones paso actual del chat de WhatsApp de cada contacto (solo lo usa el bot)
"""
import json
import os
from datetime import datetime, timezone

from sqlalchemy import (Column, Float, Integer, MetaData, String, Table, Text, create_engine, func,
                        insert, select, update)

metadata = MetaData()

solicitudes = Table(
    "solicitudes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("codigo", String(30), unique=True),            # RES-AAAAMMDD-NNNN
    Column("contacto", String(120), nullable=False, index=True),  # teléfono (WhatsApp) o id de usuario
    Column("canal", String(20), nullable=False, default="whatsapp"),
    Column("generador", String(20)),                      # hogar | negocio
    Column("categoria", String(20), nullable=False),      # ORGANICO | RECICLABLE
    Column("flujo", String(20), nullable=False),          # huerteros | recicladores (RN-01)
    Column("objeto", String(200)),                        # residuo identificado (si se supo)
    Column("metodo", String(20)),                         # texto | foto | usuario
    Column("direccion", Text),
    Column("disponibilidad", Text),
    Column("observaciones", Text),
    Column("estado", String(20), nullable=False),         # recibida|en_revision|asignada|programada|recolectada|cancelada
    Column("coordinador", String(120)),
    Column("recolector", String(120)),
    Column("dia", String(40)),
    Column("hora", String(40)),
    Column("cantidad_kg", Float),
    Column("puntos", Integer, nullable=False, default=0),
    Column("creada", String(40), nullable=False),
    Column("actualizada", String(40), nullable=False),
)

historial = Table(
    "historial", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("codigo", String(30), nullable=False, index=True),
    Column("estado", String(20), nullable=False),
    Column("actor", String(120)),
    Column("detalle", Text),
    Column("fecha", String(40), nullable=False),
)

conversaciones = Table(
    "conversaciones", metadata,
    Column("contacto", String(120), primary_key=True),
    Column("paso", String(30), nullable=False),
    Column("datos", Text, nullable=False, default="{}"),
    Column("actualizada", String(40), nullable=False),
)

_motores = {}


def url():
    u = os.environ.get("DATABASE_URL", "").strip()
    if not u:
        raise RuntimeError("Falta DATABASE_URL: este servicio solo funciona con PostgreSQL "
                           "(p. ej. postgresql://usuario:clave@localhost:5432/ecoconecta).")
    for viejo in ("postgres://", "postgresql://"):
        if u.startswith(viejo):
            u = "postgresql+psycopg://" + u[len(viejo):]
    if not u.startswith("postgresql+psycopg://"):
        raise RuntimeError("DATABASE_URL debe ser una URL de PostgreSQL (postgresql://...).")
    return u


def motor():
    u = url()
    if u not in _motores:
        _motores[u] = create_engine(u, pool_pre_ping=True)
    return _motores[u]


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def iniciar():
    metadata.create_all(motor())


def vaciar():
    """Borra todos los datos (solo para pruebas)."""
    metadata.drop_all(motor())
    metadata.create_all(motor())


def _fila(r):
    return dict(r._mapping) if r is not None else None


def crear_solicitud(datos: dict) -> str:
    """Inserta la solicitud (estado `recibida`) y devuelve su código único, p. ej. RES-20261120-0007."""
    ahora = _ahora()
    campos = {k: datos.get(k) for k in (
        "contacto", "canal", "generador", "categoria", "flujo", "objeto", "metodo",
        "direccion", "disponibilidad", "observaciones")}
    with motor().begin() as con:
        r = con.execute(insert(solicitudes).values(
            **campos, estado="recibida", puntos=0, creada=ahora, actualizada=ahora))
        n = r.inserted_primary_key[0]
        codigo = f"RES-{datetime.now(timezone.utc):%Y%m%d}-{n:04d}"
        con.execute(update(solicitudes).where(solicitudes.c.id == n).values(codigo=codigo))
        con.execute(insert(historial).values(
            codigo=codigo, estado="recibida", actor=datos.get("canal") or "usuario",
            detalle="Solicitud registrada", fecha=ahora))
    return codigo


def obtener(codigo):
    with motor().connect() as con:
        return _fila(con.execute(select(solicitudes).where(solicitudes.c.codigo == str(codigo).upper())).first())


def listar(contacto=None, flujo=None, estado=None, limite=50):
    q = select(solicitudes).order_by(solicitudes.c.id.desc()).limit(max(1, min(int(limite), 200)))
    for col, val in ((solicitudes.c.contacto, contacto), (solicitudes.c.flujo, flujo), (solicitudes.c.estado, estado)):
        if val:
            q = q.where(col == val)
    with motor().connect() as con:
        return [_fila(r) for r in con.execute(q)]


def actualizar(codigo, estado, actor=None, detalle=None, **campos):
    """Cambia el estado, guarda los campos dados y deja registro en el historial."""
    ahora = _ahora()
    with motor().begin() as con:
        con.execute(update(solicitudes).where(solicitudes.c.codigo == codigo)
                    .values(estado=estado, actualizada=ahora, **campos))
        con.execute(insert(historial).values(codigo=codigo, estado=estado, actor=actor, detalle=detalle, fecha=ahora))


def historial_de(codigo):
    with motor().connect() as con:
        q = select(historial).where(historial.c.codigo == codigo).order_by(historial.c.id)
        return [_fila(r) for r in con.execute(q)]


def puntos_de(contacto) -> int:
    with motor().connect() as con:
        q = select(func.coalesce(func.sum(solicitudes.c.puntos), 0)).where(
            solicitudes.c.contacto == contacto, solicitudes.c.estado == "recolectada")
        return int(con.execute(q).scalar())


# ---- estado de la conversación de WhatsApp
def cargar_conv(contacto):
    with motor().connect() as con:
        f = con.execute(select(conversaciones).where(conversaciones.c.contacto == contacto)).first()
    return (f.paso, json.loads(f.datos)) if f else ("MENU", {})


def guardar_conv(contacto, paso, datos):
    ahora, d = _ahora(), json.dumps(datos, ensure_ascii=False)
    with motor().begin() as con:
        if con.execute(select(conversaciones.c.contacto).where(conversaciones.c.contacto == contacto)).first():
            con.execute(update(conversaciones).where(conversaciones.c.contacto == contacto)
                        .values(paso=paso, datos=d, actualizada=ahora))
        else:
            con.execute(insert(conversaciones).values(contacto=contacto, paso=paso, datos=d, actualizada=ahora))

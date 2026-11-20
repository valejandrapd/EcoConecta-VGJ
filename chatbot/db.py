"""Almacenamiento SQLite de las solicitudes. Cada solicitud tiene un código único."""
import os
import sqlite3
from datetime import datetime, timezone

RUTA = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "solicitudes.db"))


def _conectar():
    con = sqlite3.connect(RUTA)
    con.row_factory = sqlite3.Row
    return con


def iniciar():
    with _conectar() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS solicitudes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                telefono TEXT NOT NULL,
                descripcion TEXT,
                categoria TEXT,          -- ORGANICO | RECICLABLE | OTRO | NULL
                metodo TEXT,             -- texto | foto
                estado TEXT NOT NULL,    -- resuelta | esperando_foto
                creada TEXT NOT NULL
            )"""
        )


def crear(telefono, descripcion):
    """Crea una solicitud y devuelve su código único, p. ej. RES-20261120-0007."""
    ahora = datetime.now(timezone.utc)
    with _conectar() as con:
        cur = con.execute(
            "INSERT INTO solicitudes (telefono, descripcion, estado, creada) VALUES (?, ?, 'esperando_foto', ?)",
            (telefono, descripcion, ahora.isoformat()),
        )
        codigo = f"RES-{ahora:%Y%m%d}-{cur.lastrowid:04d}"
        con.execute("UPDATE solicitudes SET codigo = ? WHERE id = ?", (codigo, cur.lastrowid))
    return codigo


def resolver(codigo, categoria, metodo):
    with _conectar() as con:
        con.execute(
            "UPDATE solicitudes SET categoria = ?, metodo = ?, estado = 'resuelta' WHERE codigo = ?",
            (categoria, metodo, codigo),
        )


def pendiente_de_foto(telefono):
    """Última solicitud de ese teléfono que sigue esperando una foto."""
    with _conectar() as con:
        fila = con.execute(
            "SELECT * FROM solicitudes WHERE telefono = ? AND estado = 'esperando_foto' ORDER BY id DESC LIMIT 1",
            (telefono,),
        ).fetchone()
    return dict(fila) if fila else None


def obtener(codigo):
    with _conectar() as con:
        fila = con.execute("SELECT * FROM solicitudes WHERE codigo = ?", (codigo.upper(),)).fetchone()
    return dict(fila) if fila else None

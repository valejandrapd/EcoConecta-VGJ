"""Almacenamiento SQLite de las solicitudes. Cada solicitud tiene un código único.

`contacto` identifica a quien pide: un teléfono (WhatsApp), un id de usuario de la app, un correo, etc.
`canal` dice por dónde llegó: whatsapp | api | web | app ...
"""
import os
import sqlite3
from datetime import datetime, timezone


def ruta():
    """Archivo de la base de datos (variable DB_PATH; por defecto chatbot/solicitudes.db)."""
    return os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "solicitudes.db"))


def _conectar():
    con = sqlite3.connect(ruta())
    con.row_factory = sqlite3.Row
    return con


def iniciar():
    with _conectar() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS solicitudes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                contacto TEXT NOT NULL,
                canal TEXT NOT NULL DEFAULT 'whatsapp',
                descripcion TEXT,
                categoria TEXT,          -- ORGANICO | RECICLABLE | OTRO | NULL
                objeto TEXT,             -- nombre del residuo, si se identificó por foto
                metodo TEXT,             -- texto | foto
                estado TEXT NOT NULL,    -- resuelta | esperando_foto
                creada TEXT NOT NULL
            )"""
        )
        # Migración de la primera versión (columna `telefono`, sin `canal` ni `objeto`).
        columnas = {f["name"] for f in con.execute("PRAGMA table_info(solicitudes)")}
        if "telefono" in columnas and "contacto" not in columnas:
            con.execute("ALTER TABLE solicitudes RENAME COLUMN telefono TO contacto")
        if "canal" not in columnas:
            con.execute("ALTER TABLE solicitudes ADD COLUMN canal TEXT NOT NULL DEFAULT 'whatsapp'")
        if "objeto" not in columnas:
            con.execute("ALTER TABLE solicitudes ADD COLUMN objeto TEXT")


def crear(contacto, descripcion, canal="whatsapp"):
    """Crea una solicitud y devuelve su código único, p. ej. RES-20261120-0007."""
    ahora = datetime.now(timezone.utc)
    with _conectar() as con:
        cur = con.execute(
            "INSERT INTO solicitudes (contacto, canal, descripcion, estado, creada) "
            "VALUES (?, ?, ?, 'esperando_foto', ?)",
            (contacto, canal, descripcion, ahora.isoformat()),
        )
        codigo = f"RES-{ahora:%Y%m%d}-{cur.lastrowid:04d}"
        con.execute("UPDATE solicitudes SET codigo = ? WHERE id = ?", (codigo, cur.lastrowid))
    return codigo


def resolver(codigo, categoria, metodo, objeto=""):
    with _conectar() as con:
        con.execute(
            "UPDATE solicitudes SET categoria = ?, metodo = ?, objeto = ?, estado = 'resuelta' WHERE codigo = ?",
            (categoria, metodo, objeto or None, codigo),
        )


def pendiente_de_foto(contacto):
    """Última solicitud de ese contacto que sigue esperando una foto."""
    with _conectar() as con:
        fila = con.execute(
            "SELECT * FROM solicitudes WHERE contacto = ? AND estado = 'esperando_foto' ORDER BY id DESC LIMIT 1",
            (contacto,),
        ).fetchone()
    return dict(fila) if fila else None


def obtener(codigo):
    with _conectar() as con:
        fila = con.execute("SELECT * FROM solicitudes WHERE codigo = ?", (codigo.upper(),)).fetchone()
    return dict(fila) if fila else None


def listar(contacto=None, limite=50):
    """Solicitudes más recientes primero; opcionalmente solo las de un contacto."""
    limite = max(1, min(int(limite), 200))
    with _conectar() as con:
        if contacto:
            filas = con.execute(
                "SELECT * FROM solicitudes WHERE contacto = ? ORDER BY id DESC LIMIT ?", (contacto, limite)
            ).fetchall()
        else:
            filas = con.execute("SELECT * FROM solicitudes ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(f) for f in filas]

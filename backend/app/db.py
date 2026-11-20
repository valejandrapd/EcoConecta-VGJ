"""Conexión a PostgreSQL (única base de datos permitida)."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import config


class Base(DeclarativeBase):
    pass


_engine = None
_Session = None


def engine():
    global _engine, _Session
    if _engine is None:
        url = config().database_url
        if not url.startswith("postgresql"):
            raise RuntimeError("DATABASE_URL debe apuntar a PostgreSQL (regla del reto).")
        _engine = create_engine(url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def reiniciar_engine():
    """Para pruebas: descarta el engine cacheado."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = _Session = None


@contextmanager
def sesion():
    engine()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def crear_tablas():
    from . import models  # noqa: F401  (registra los modelos)
    Base.metadata.create_all(engine())
    _agregar_columnas_nuevas()
    _migrar_perfiles()


def _migrar_perfiles():
    """Perfiles anteriores: los coordinadores cambian de nombre y las cuentas de huerteros y
    recicladores se desactivan (ahora son personal de campo sin acceso, en `personal_campo`)."""
    from sqlalchemy import text
    with engine().begin() as con:
        con.execute(text("UPDATE usuarios SET rol = 'coordinador_huerta' WHERE rol = 'coordinador_huerteros'"))
        con.execute(text("UPDATE usuarios SET rol = 'coordinador_reciclaje' WHERE rol = 'coordinador_recicladores'"))
        con.execute(text("UPDATE usuarios SET activo = false WHERE rol IN ('huertero', 'reciclador') AND activo"))


def _agregar_columnas_nuevas():
    """Migración mínima: create_all no altera tablas existentes, así que agrega las columnas
    nuevas (todas opcionales) a una base creada con una versión anterior."""
    from sqlalchemy import inspect, text
    eng = engine()
    insp = inspect(eng)
    with eng.begin() as con:
        for tabla in Base.metadata.sorted_tables:
            if not insp.has_table(tabla.name):
                continue
            existentes = {c["name"] for c in insp.get_columns(tabla.name)}
            for col in tabla.columns:
                if col.name not in existentes and col.nullable:
                    tipo = col.type.compile(dialect=eng.dialect)
                    con.execute(text(f'ALTER TABLE {tabla.name} ADD COLUMN IF NOT EXISTS "{col.name}" {tipo}'))

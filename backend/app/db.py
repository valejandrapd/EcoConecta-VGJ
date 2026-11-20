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

"""Datos de demostración: cada sección de "Aprende sobre residuos" tiene contenido y no se duplica."""
from sqlalchemy import func, select

from app import seed
from app.db import sesion
from app.models import Contenido


def test_cada_seccion_tiene_contenido_y_no_se_duplica(monkeypatch):
    monkeypatch.setenv("DEMO_CLAVE", "demo1234")
    seed.cargar()
    seed.cargar()
    with sesion() as s:
        tipos = set(s.scalars(select(Contenido.tipo)))
        total = s.scalar(select(func.count(Contenido.id)))
    assert {"tutorial", "huerta", "horario", "ruta", "general"} <= tipos
    assert total == len(seed.CONTENIDOS)

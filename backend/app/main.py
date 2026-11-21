"""Backend de EcoConecta (FastAPI + PostgreSQL)."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.cuentas import router as cuentas_router
from .api.rutas import router as api_router
from .db import crear_tablas, sesion
from .whatsapp.mensajeria import purgar_vencidos
from .whatsapp.webhook import router as webhook_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def ciclo(_app):
    crear_tablas()
    with sesion() as s:
        purgar_vencidos(s)
    if os.environ.get("SEMBRAR_DEMO", "").strip().lower() in {"1", "true", "si", "sí"}:
        # Despliegue de demostración (Azure): carga zonas, personal y usuarios demo si faltan.
        from .seed import cargar
        cargar()
    yield


app = FastAPI(title="EcoConecta", lifespan=ciclo)
app.include_router(webhook_router)
app.include_router(api_router)
app.include_router(cuentas_router)


@app.get("/health")
def health():
    return {"ok": True}

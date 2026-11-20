"""Datos de demostración: `python -m app.seed`. Teléfonos ficticios; cámbialos por los del número de prueba."""
import os
from datetime import date, time

from sqlalchemy import select, text

from .db import crear_tablas, sesion
from .models import Contenido, Solicitud, Usuario
from .telefono import normalizar

CONTENIDOS = [
    ("tutorial", "Cómo separar en casa",
     "Usa dos recipientes: orgánicos (restos de comida, cáscaras, hojas) y reciclables (plástico, vidrio, "
     "metal, papel y cartón limpios y secos). Lo que esté sucio o sea higiénico va a ordinarios.",
     "separar,separo,tutorial,como separo", None),
    ("horario", "Horario de recolección de orgánicos",
     "Martes y viernes de 7:00 a. m. a 11:00 a. m.", "horario organico,horario,horarios", "organico"),
    ("horario", "Horario de recolección de reciclables",
     "Miércoles y sábado de 8:00 a. m. a 12:00 m.", "horario reciclable,horario,horarios", "reciclable"),
    ("ruta", "Rutas por barrio",
     "Ruta 1: Centro y La Candelaria. Ruta 2: Chapinero y Teusaquillo. Pregunta a la coordinación por tu barrio.",
     "ruta,rutas,barrio", None),
]


def cargar():
    crear_tablas()
    with sesion() as s:
        if s.scalar(select(Contenido.id).limit(1)) is None:
            for tipo, titulo, cuerpo, claves, flujo in CONTENIDOS:
                s.add(Contenido(tipo=tipo, titulo=titulo, cuerpo=cuerpo, palabras_clave=claves, flujo=flujo))
        demo = normalizar(os.environ.get("DEMO_TELEFONO", "+573000000001"))
        if not s.scalar(select(Usuario).where(Usuario.telefono == demo)):
            ana = Usuario(nombre="Ana Demo", telefono=demo, direccion="Calle 1 # 2-3", rol="ciudadano")
            carlos = Usuario(nombre="Carlos Recolector", telefono="+573000000002", rol="recolector")
            s.add_all([ana, carlos,
                       Usuario(nombre="Coordinación Orgánicos", telefono="+573000000003", rol="coordinador", flujo="organico"),
                       Usuario(nombre="Coordinación Reciclables", telefono="+573000000004", rol="coordinador", flujo="reciclable")])
            s.flush()
            s.add(Solicitud(codigo="ORG-0042", usuario=ana, flujo="organico", estado="programada",
                            fecha_programada=date.today(), hora_programada=time(8, 0), encargado=carlos))
        s.execute(text("SELECT setval('seq_codigo_org', GREATEST(42, (SELECT last_value FROM seq_codigo_org)))"))
    print("Datos de demostración cargados.")


if __name__ == "__main__":
    cargar()

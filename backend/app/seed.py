"""Datos FICTICIOS de demostración: `python -m app.seed`.

DEMO_TELEFONO permite usar tu número (destinatario de prueba en Meta) como la unidad productiva.
Los contenidos son ejemplos: deben reemplazarse por el material validado por FSD y los huerteros.
"""
import os
import secrets
from datetime import date, time

from sqlalchemy import select, text

from .auth import hash_clave
from .db import crear_tablas, sesion
from .models import Contenido, HistorialSolicitud, Solicitud, Usuario
from .telefono import normalizar

CONTENIDOS = [
    ("tutorial", "Cómo separar en casa o en tu negocio",
     "Usa dos recipientes: orgánicos (restos de comida, cáscaras, borra de café, hojas) y reciclables "
     "(plástico, vidrio, metal, papel y cartón limpios y secos). Lo sucio o higiénico va a ordinarios.",
     "separar,separo,tutorial,como separo", None),
    ("tutorial", "¿Qué pasa con tus orgánicos?",
     "Los huerteros los llevan a la huerta comunitaria, los clasifican y los compostan para producir abono.",
     "huerta,compost,compostaje,abono", "organico"),
    ("horario", "Horario de recolección de orgánicos (ejemplo)",
     "Negocios: todos los días. Hogares: día de por medio. La hora se acuerda con el huertero asignado.",
     "horario organico,horario,horarios", "organico"),
    ("horario", "Horario de recolección de reciclables (ejemplo)",
     "Según el cronograma de los recicladores de oficio; la coordinación confirma día y hora al programar.",
     "horario reciclable,horario,horarios", "reciclable"),
    ("ruta", "Rutas en Villas de San Pablo (ejemplo)",
     "La coordinación organiza las rutas por sector según las solicitudes de la semana. "
     "También puedes llevar tus reciclables al punto de recolección comunitario.",
     "ruta,rutas,sector,punto de recoleccion", None),
]

# (nombre, telefono, rol, tipo_generador, direccion)
USUARIOS = [
    ("Tienda La Esquina (demo)", None, "solicitante", "unidad_productiva", "Manzana 10, local 3"),
    ("Hogar Pérez (demo)", "+573000000005", "solicitante", "hogar", "Manzana 4, casa 12"),
    ("Coord. Huerteros (demo)", "+573000000003", "coordinador_huerteros", None, None),
    ("Coord. Recicladores (demo)", "+573000000004", "coordinador_recicladores", None, None),
    ("Carlos Huertero (demo)", "+573000000002", "huertero", None, None),
    ("Rosa Recicladora (demo)", "+573000000006", "reciclador", None, None),
    ("Admin EcoConecta (demo)", "+573000000007", "administrador", None, None),
]


def cargar():
    crear_tablas()
    demo = normalizar(os.environ.get("DEMO_TELEFONO", "+573000000001"))
    clave = os.environ.get("DEMO_CLAVE") or secrets.token_urlsafe(9)
    with sesion() as s:
        if s.scalar(select(Contenido.id).limit(1)) is None:
            for tipo, titulo, cuerpo, claves, flujo in CONTENIDOS:
                s.add(Contenido(tipo=tipo, titulo=titulo, cuerpo=cuerpo, palabras_clave=claves, flujo=flujo))
        if s.scalar(select(Usuario.id).where(Usuario.rol == "administrador").limit(1)) is None:
            creados = {}
            for nombre, tel, rol, tipo, direccion in USUARIOS:
                u = Usuario(nombre=nombre, telefono=tel or demo, rol=rol, tipo_generador=tipo,
                            direccion=direccion, piloto=True, clave_hash=hash_clave(clave))
                s.add(u)
                creados[rol if rol != "solicitante" else nombre] = u
            s.flush()
            tienda, coord, carlos = creados["Tienda La Esquina (demo)"], creados["coordinador_huerteros"], creados["huertero"]
            sol = Solicitud(codigo="ORG-0042", usuario=tienda, flujo="organico", tipo_generador="unidad_productiva",
                            estado="programada", direccion=tienda.direccion, disponibilidad="Lun, Mié, Vie · 07:00 a 10:00",
                            tamano="grande", dias_disponibles="lun,mie,vie", hora_desde=time(7, 0),
                            hora_hasta=time(10, 0), bonificacion="huerto",
                            coordinador=coord, recolector=carlos,
                            fecha_programada=date.today(), hora_programada=time(8, 0))
            s.add(sol)
            s.flush()
            for de, a in [(None, "recibida"), ("recibida", "asignada"), ("asignada", "programada")]:
                s.add(HistorialSolicitud(solicitud_id=sol.id, estado_anterior=de, estado_nuevo=a, actor_id=coord.id))
            if not os.environ.get("DEMO_CLAVE"):
                print(f"Clave de los usuarios demo (generada, guárdala): {clave}")
        s.execute(text("SELECT setval('seq_codigo_org', GREATEST(42, (SELECT last_value FROM seq_codigo_org)))"))
    print("Datos de demostración cargados.")


if __name__ == "__main__":
    cargar()

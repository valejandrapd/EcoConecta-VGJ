"""Datos FICTICIOS de demostración: `python -m app.seed`.

DEMO_TELEFONO permite usar tu número (destinatario de prueba en Meta) como la unidad productiva.
Los contenidos son ejemplos: deben reemplazarse por el material validado por FSD y los voluntarios de huerta.
"""
import os
import secrets
from datetime import date, time, timedelta

from sqlalchemy import select, text

from .auth import hash_clave
from .db import crear_tablas, sesion
from .models import Contenido, HistorialSolicitud, PersonalCampo, Solicitud, Usuario
from .telefono import normalizar

CONTENIDOS = [
    ("tutorial", "Cómo separar en casa o en tu negocio",
     "Usa dos recipientes: orgánicos (restos de comida, cáscaras, borra de café, hojas) y reciclables "
     "(plástico, vidrio, metal, papel y cartón limpios y secos). Lo sucio o higiénico va a ordinarios.",
     "separar,separo,tutorial,como separo", None),
    ("tutorial", "¿Qué pasa con tus orgánicos?",
     "Los recicladores los llevan a la huerta comunitaria, donde los voluntarios de huerta los compostan para producir abono.",
     "huerta,compost,compostaje,abono", "organico"),
    ("horario", "Horario de recolección de orgánicos (ejemplo)",
     "Negocios: todos los días. Hogares: día de por medio. La coordinación confirma día y hora según tu disponibilidad.",
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
    ("Coord. Huerta (demo)", "+573000000003", "coordinador_huerta", None, None),
    ("Coord. Reciclaje (demo)", "+573000000004", "coordinador_reciclaje", None, None),
    ("Admin EcoConecta (demo)", "+573000000007", "administrador", None, None),
]
ZONA_DEMO = {"Tienda La Esquina (demo)": "Sector 1", "Hogar Pérez (demo)": "Sector 2"}

# Personal de campo sin cuenta: (tipo, nombre, apellido, zona, días, desde, hasta)
PERSONAL = [
    ("reciclador", "Rosa", "Martínez", "Sector 1", "lun,mar,mie,jue,vie", time(7, 0), time(12, 0)),
    ("reciclador", "Luis", "Herrera", "Sector 2", "lun,mie,vie,sab", time(8, 0), time(17, 0)),
    ("reciclador", "Marta", "Rincón", "Sector 2", "mar,jue,sab", time(13, 0), time(18, 0)),
    ("voluntario_huerta", "Carlos", "Ruiz", None, "sab,dom", time(7, 0), time(11, 0)),
]


def cargar():
    crear_tablas()
    demo = normalizar(os.environ.get("DEMO_TELEFONO", "+573000000001"))
    clave = os.environ.get("DEMO_CLAVE") or secrets.token_urlsafe(9)
    with sesion() as s:
        if s.scalar(select(Contenido.id).limit(1)) is None:
            for tipo, titulo, cuerpo, claves, flujo in CONTENIDOS:
                s.add(Contenido(tipo=tipo, titulo=titulo, cuerpo=cuerpo, palabras_clave=claves, flujo=flujo))
        # Personal de campo (también en bases creadas antes de que existiera)
        if s.scalar(select(PersonalCampo.id).limit(1)) is None:
            for tipo, nombre, apellido, zona, dias, desde, hasta in PERSONAL:
                s.add(PersonalCampo(tipo=tipo, nombre=nombre, apellido=apellido, zona=zona, dias_servicio=dias,
                                    hora_desde=desde, hora_hasta=hasta))
            s.flush()
        rosa = s.scalar(select(PersonalCampo).where(PersonalCampo.nombre == "Rosa"))
        if s.scalar(select(Usuario.id).where(Usuario.rol == "administrador").limit(1)) is None:
            creados = {}
            for nombre, tel, rol, tipo, direccion in USUARIOS:
                u = Usuario(nombre=nombre, telefono=tel or demo, rol=rol, tipo_generador=tipo, direccion=direccion,
                            zona=ZONA_DEMO.get(nombre), piloto=True, clave_hash=hash_clave(clave))
                s.add(u)
                creados[rol if rol != "solicitante" else nombre] = u
            s.flush()
            tienda, coord = creados["Tienda La Esquina (demo)"], creados["coordinador_huerta"]
            # Programada para el próximo lunes, miércoles o viernes a las 08:00 (ventana del usuario y de Rosa)
            dia = date.today() + timedelta(days=1)
            while dia.weekday() not in (0, 2, 4):
                dia += timedelta(days=1)
            sol = Solicitud(codigo="ORG-0042", usuario=tienda, flujo="organico", tipo_generador="unidad_productiva",
                            estado="programada", direccion=tienda.direccion, zona=tienda.zona,
                            disponibilidad="Lun, Mié, Vie · 07:00 a 10:00",
                            tamano="grande", dias_disponibles="lun,mie,vie", hora_desde=time(7, 0),
                            hora_hasta=time(10, 0), bonificacion="huerto",
                            coordinador=coord, reciclador=rosa, fecha_programada=dia, hora_programada=time(8, 0))
            s.add(sol)
            s.flush()
            for de, a in [(None, "recibida"), ("recibida", "asignada"), ("asignada", "programada")]:
                s.add(HistorialSolicitud(solicitud_id=sol.id, estado_anterior=de, estado_nuevo=a, actor_id=coord.id))
            if not os.environ.get("DEMO_CLAVE"):
                print(f"Clave de los usuarios demo (generada, guárdala): {clave}")
        else:
            # Base de demostración anterior: nombres de perfiles nuevos y zonas que falten
            for viejo, nuevo in (("Coord. Huerteros (demo)", "Coord. Huerta (demo)"),
                                 ("Coord. Recicladores (demo)", "Coord. Reciclaje (demo)")):
                u = s.scalar(select(Usuario).where(Usuario.nombre == viejo))
                if u:
                    u.nombre = nuevo
            for nombre, zona in ZONA_DEMO.items():
                u = s.scalar(select(Usuario).where(Usuario.nombre == nombre))
                if u and not u.zona:
                    u.zona = zona
            sol = s.scalar(select(Solicitud).where(Solicitud.codigo == "ORG-0042"))
            if sol and not sol.reciclador_id and sol.estado in ("asignada", "programada"):
                sol.zona, sol.reciclador = sol.zona or "Sector 1", rosa
        s.execute(text("SELECT setval('seq_codigo_org', GREATEST(42, (SELECT last_value FROM seq_codigo_org)))"))
    print("Datos de demostración cargados.")


if __name__ == "__main__":
    cargar()

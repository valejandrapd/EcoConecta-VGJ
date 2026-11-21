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
from .models import Contenido, HistorialSolicitud, PersonalCampo, Solicitud, Usuario, Zona
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
    ("huerta", "La huerta comunitaria",
     "Es un espacio de la comunidad de Villas de San Pablo. Los voluntarios de huerta siembran y convierten los "
     "residuos orgánicos del barrio en abono, así tus cáscaras vuelven a la tierra en lugar de ir a la basura.",
     "huerta,huerta comunitaria,voluntarios,voluntario de huerta", "organico"),
    ("huerta", "Cómo se hace el compost",
     "En la huerta los orgánicos se revisan, se mezclan con hojas secas y se dejan descomponer, volteándolos de vez "
     "en cuando. Con el tiempo se vuelven abono para las siembras. Por eso deben llegar sin plásticos ni stickers.",
     "compost,compostaje,abono,como se hace el compost", "organico"),
    ("huerta", "Qué recibe la huerta y qué no",
     "Sí: cáscaras de frutas y verduras, borra de café, cáscaras de huevo, hojas y flores. No: carne, huesos, "
     "lácteos, grasa, comida con aceite, heces de mascotas ni papel higiénico, porque atraen plagas o dañan el compost.",
     "que recibe la huerta,carne,huesos,lacteos,que no va", "organico"),
    ("huerta", "Servicios del huerto con tus puntos",
     "Al pedir una recolección puedes elegir que tus puntos sean para servicios del huerto. Tu trinitaria crece cada "
     "5 puntos. Los servicios disponibles los define la huerta con la Fundación Santo Domingo.",
     "servicios del huerto,trinitaria,puntos huerta", None),
    ("general", "¿Qué es EcoConecta?",
     "Es el canal único de Villas de San Pablo para aprender a separar, pedir la recolección de tus residuos y "
     "seguirla. Lo usas desde la web o por WhatsApp, y no reemplaza el voz a voz ni a los líderes del barrio: los apoya.",
     "que es ecoconecta,ecoconecta,canal", None),
    ("general", "Quiénes participan",
     "Hogares y negocios que separan; recicladores de oficio que recogen orgánicos y reciclables; voluntarios de "
     "huerta que hacen el compost; y la coordinación de huerta y de reciclaje, que organiza las visitas. En el barrio "
     "también apoyan el punto de recolección comunitario y entidades como la Alcaldía, Siembra Barranquilla y Asorescatar.",
     "quienes participan,actores,recicladores,asorescatar,siembra barranquilla", None),
    ("general", "Cómo funcionan los puntos",
     "Los puntos se suman solo cuando la coordinación registra la recolección: unos puntos base más puntos por kilo. "
     "Son valores de ejemplo del piloto, sujetos a validación de la Fundación Santo Domingo.",
     "puntos,como gano puntos,kilos,alcancia", None),
    ("general", "Tus datos están protegidos",
     "Solo pedimos lo necesario para atender tu solicitud. Tu teléfono y dirección solo los ve la coordinación que la "
     "atiende, y las fotos que envías no se guardan.",
     "datos,privacidad,mis datos", None),
]

# (nombre, telefono, rol, tipo_generador, direccion)
USUARIOS = [
    ("Tienda La Esquina (demo)", None, "solicitante", "unidad_productiva", "Manzana 10, local 3"),
    ("Hogar Pérez (demo)", "+573000000005", "solicitante", "hogar", "Manzana 4, casa 12"),
    ("Coord. Huerta (demo)", "+573000000003", "coordinador_huerta", None, None),
    ("Coord. Reciclaje (demo)", "+573000000004", "coordinador_reciclaje", None, None),
    ("Admin EcoConecta (demo)", "+573000000007", "administrador", None, None),
]
ZONAS = [f"Sector {i}" for i in range(1, 8)]  # ficticias; el mapa de la coordinación dibuja siete sectores
ZONA_DEMO = {"Tienda La Esquina (demo)": "Sector 1", "Hogar Pérez (demo)": "Sector 2"}

# Personal de campo sin cuenta: (tipo, nombre, apellido, zona, días, desde, hasta)
PERSONAL = [
    ("reciclador", "Rosa", "Martínez", "Sector 1", "lun,mar,mie,jue,vie", time(7, 0), time(12, 0)),
    ("reciclador", "Luis", "Herrera", "Sector 2", "lun,mie,vie,sab", time(8, 0), time(17, 0)),
    ("reciclador", "Marta", "Rincón", "Sector 2", "mar,jue,sab", time(13, 0), time(18, 0)),
    ("reciclador", "Andrés", "Pérez", "Sector 3", "lun,mar,mie,jue,vie", time(8, 0), time(16, 0)),
    ("reciclador", "Yaneth", "Cuesta", "Sector 4", "mar,jue,sab", time(6, 0), time(12, 0)),
    ("reciclador", "Jorge", "Mendoza", "Sector 5", "lun,mie,vie", time(13, 0), time(18, 0)),
    ("reciclador", "Dayana", "Ortiz", "Sector 6", "lun,mar,mie,jue,vie,sab", time(7, 0), time(15, 0)),
    ("reciclador", "Wilson", "Barrios", "Sector 7", "mie,jue,vie,sab,dom", time(9, 0), time(17, 0)),
    ("voluntario_huerta", "Carlos", "Ruiz", None, "sab,dom", time(7, 0), time(11, 0)),
]


def cargar():
    crear_tablas()
    demo = normalizar(os.environ.get("DEMO_TELEFONO", "+573000000001"))
    clave = os.environ.get("DEMO_CLAVE") or secrets.token_urlsafe(9)
    with sesion() as s:
        # Contenidos de ejemplo para cada sección vacía. Una base ya cargada recibe las secciones nuevas
        # sin duplicar, y lo que el administrador borró de una sección con contenido no vuelve.
        con_contenido = set(s.scalars(select(Contenido.tipo)))
        for tipo, titulo, cuerpo, claves, flujo in CONTENIDOS:
            if tipo not in con_contenido:
                s.add(Contenido(tipo=tipo, titulo=titulo, cuerpo=cuerpo, palabras_clave=claves, flujo=flujo))
        # Zonas ficticias (el administrador las cambia desde la web)
        if s.scalar(select(Zona.id).limit(1)) is None:
            s.add_all([Zona(nombre=z) for z in ZONAS])
            s.flush()
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

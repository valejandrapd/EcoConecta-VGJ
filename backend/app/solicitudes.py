"""Reglas de negocio de solicitudes (RN-01 a RN-06).

Las decisiones operativas (asignar, programar, cerrar) las toman PERSONAS con su perfil.
La IA nunca llama a este módulo.
"""
import math
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import select

from .config import config
from .models import (BONIFICACIONES, COORDINADOR_DE_FLUJO, DIAS_SEMANA, PREFIJO_FLUJO, SEQ_ORG, SEQ_REC, TAMANOS,
                     TIPOS_GENERADOR, DireccionUsuario, HistorialSolicitud, PersonalCampo, Recoleccion, Solicitud,
                     Usuario, Zona)
from .notificaciones import obtener_notificador


class ErrorSolicitud(ValueError):
    pass


class SinPermiso(PermissionError):
    pass


def _nuevo_codigo(s, flujo: str) -> str:
    seq = SEQ_ORG if flujo == "organico" else SEQ_REC
    return f"{PREFIJO_FLUJO[flujo]}-{s.scalar(seq.next_value()):04d}"


def _cambiar_estado(s, sol: Solicitud, nuevo: str, actor: Usuario | None, nota: str | None = None):
    s.add(HistorialSolicitud(solicitud_id=sol.id, estado_anterior=sol.estado, estado_nuevo=nuevo,
                             actor_id=actor.id if actor else None, nota=nota))
    sol.estado = nuevo


def _es_coordinador(actor: Usuario, sol: Solicitud) -> bool:
    return actor.rol == "administrador" or actor.rol == COORDINADOR_DE_FLUJO[sol.flujo]


def _exigir_coordinador(actor: Usuario, sol: Solicitud):
    if not _es_coordinador(actor, sol):
        raise SinPermiso("Solo el coordinador del flujo puede hacer esto")


def obtener(s, codigo: str) -> Solicitud:
    sol = s.scalar(select(Solicitud).where(Solicitud.codigo == codigo.upper()))
    if not sol:
        raise ErrorSolicitud("No existe esa solicitud")
    return sol


def puede_ver_contacto(actor: Usuario, sol: Solicitud) -> bool:
    """RN-07: contacto y ubicación solo para su dueño y la coordinación del flujo."""
    return actor.id == sol.usuario_id or _es_coordinador(actor, sol)


NOMBRE_DIA = {"lun": "Lun", "mar": "Mar", "mie": "Mié", "jue": "Jue", "vie": "Vie", "sab": "Sáb", "dom": "Dom"}


def texto_disponibilidad(dias: list[str] | None, desde: time | None, hasta: time | None) -> str | None:
    """Resumen legible para coordinadores y para el bot: "Lun, Mié · 08:00 a 12:00"."""
    partes = []
    if dias:
        partes.append(", ".join(NOMBRE_DIA[d] for d in DIAS_SEMANA if d in dias))
    if desde and hasta:
        partes.append(f"{desde:%H:%M} a {hasta:%H:%M}")
    return " · ".join(partes) or None


def _validar_detalle(tamano, dias, hora_desde, hora_hasta, bonificacion, direccion_etiqueta):
    if tamano is not None and tamano not in TAMANOS:
        raise ErrorSolicitud("tamano debe ser 'pequeno', 'mediano' o 'grande'")
    if dias is not None:
        if not dias or any(d not in DIAS_SEMANA for d in dias):
            raise ErrorSolicitud("Elige al menos un día válido (lun a dom)")
    if (hora_desde is None) != (hora_hasta is None):
        raise ErrorSolicitud("Indica la hora de inicio y la de fin")
    if hora_desde and hora_desde >= hora_hasta:
        raise ErrorSolicitud("La hora de inicio debe ser anterior a la de fin")
    if bonificacion is not None and bonificacion not in BONIFICACIONES:
        raise ErrorSolicitud("bonificacion debe ser 'tiendas' o 'huerto'")
    if direccion_etiqueta is not None and not direccion_etiqueta.strip():
        raise ErrorSolicitud("La etiqueta de la dirección no puede estar vacía")


def zonas_activas(s) -> list[str]:
    return list(s.scalars(select(Zona.nombre).where(Zona.activa.is_(True)).order_by(Zona.nombre)))


def _validar_zona(s, zona: str | None):
    if zona is not None and zona not in zonas_activas(s):
        raise ErrorSolicitud("Zona desconocida")


def _guardar_direccion(s, usuario: Usuario, etiqueta: str, direccion: str, zona: str | None):
    """Guarda (o actualiza) la dirección etiquetada para reutilizarla en otra solicitud."""
    d = s.scalar(select(DireccionUsuario).where(DireccionUsuario.usuario_id == usuario.id,
                                                DireccionUsuario.etiqueta == etiqueta))
    if d:
        d.direccion, d.zona = direccion, zona
    else:
        s.add(DireccionUsuario(usuario_id=usuario.id, etiqueta=etiqueta, direccion=direccion, zona=zona))


def crear(s, usuario: Usuario, flujo: str, *, tipo_generador: str | None = None, observaciones: str = "",
          direccion: str | None = None, disponibilidad: str | None = None, tamano: str | None = None,
          dias: list[str] | None = None, hora_desde: time | None = None, hora_hasta: time | None = None,
          direccion_etiqueta: str | None = None, bonificacion: str | None = None,
          zona: str | None = None) -> Solicitud:
    if flujo not in PREFIJO_FLUJO:
        raise ErrorSolicitud("flujo debe ser 'organico' o 'reciclable'")
    tipo = tipo_generador or usuario.tipo_generador or "hogar"
    if tipo not in TIPOS_GENERADOR:
        raise ErrorSolicitud("tipo_generador debe ser 'hogar' o 'unidad_productiva'")
    if config().modo_piloto and not usuario.piloto:
        raise SinPermiso("El usuario no está habilitado en el piloto (RN-08)")
    _validar_detalle(tamano, dias, hora_desde, hora_hasta, bonificacion, direccion_etiqueta)
    _validar_zona(s, zona)
    propia = (direccion or "").strip()
    direccion = propia or usuario.direccion
    if not direccion:
        raise ErrorSolicitud("Falta la dirección")
    etiqueta = direccion_etiqueta.strip() if direccion_etiqueta else None
    if direccion == usuario.direccion:
        if zona and not usuario.zona:
            usuario.zona = zona  # completa el perfil la primera vez
        zona = zona or usuario.zona
    elif etiqueta:
        _guardar_direccion(s, usuario, etiqueta, direccion, zona)
    sol = Solicitud(codigo=_nuevo_codigo(s, flujo), usuario=usuario, flujo=flujo, tipo_generador=tipo,
                    estado="recibida", observaciones=observaciones or None, direccion=direccion,
                    disponibilidad=disponibilidad or texto_disponibilidad(dias, hora_desde, hora_hasta),
                    tamano=tamano, dias_disponibles=",".join(d for d in DIAS_SEMANA if d in dias) if dias else None,
                    hora_desde=hora_desde, hora_hasta=hora_hasta, direccion_etiqueta=etiqueta,
                    zona=zona, bonificacion=bonificacion)
    s.add(sol)
    s.flush()
    s.add(HistorialSolicitud(solicitud_id=sol.id, estado_nuevo="recibida", actor_id=usuario.id))
    n = obtener_notificador()
    n.solicitud_recibida(s, sol)
    n.nueva_solicitud(s, sol)  # RN-01: solo a la coordinación del flujo
    return sol


def revisar(s, sol: Solicitud, actor: Usuario) -> Solicitud:
    _exigir_coordinador(actor, sol)
    if sol.estado != "recibida":
        raise ErrorSolicitud("Solo se revisan solicitudes recibidas")
    sol.coordinador_id = actor.id
    _cambiar_estado(s, sol, "en_revision", actor)
    return sol


def _rango(desde: time | None, hasta: time | None) -> tuple[time, time]:
    return desde or time(0, 0), hasta or time(23, 59)


def ventana(sol: Solicitud, rec: PersonalCampo) -> dict | None:
    """Días y horas en que el reciclador puede recoger ESTA solicitud: lo que eligió el usuario
    cruzado con el servicio del reciclador. None si no es compatible (otra zona o sin cruce)."""
    if rec.tipo != "reciclador" or not rec.activo:
        return None
    if sol.zona and rec.zona != sol.zona:
        return None
    dias_sol = sol.dias_disponibles.split(",") if sol.dias_disponibles else list(DIAS_SEMANA)
    dias = [d for d in DIAS_SEMANA if d in dias_sol and d in rec.dias]
    a1, b1 = _rango(sol.hora_desde, sol.hora_hasta)
    a2, b2 = _rango(rec.hora_desde, rec.hora_hasta)
    desde, hasta = max(a1, a2), min(b1, b2)
    if not dias or desde >= hasta:
        return None
    return {"dias": dias, "desde": desde, "hasta": hasta}


def fechas_posibles(v: dict, desde: date | None = None, semanas: int = 3) -> list[date]:
    hoy = desde or date.today()
    return [hoy + timedelta(days=i) for i in range(semanas * 7)
            if DIAS_SEMANA[(hoy + timedelta(days=i)).weekday()] in v["dias"]]


def opciones_asignacion(s, sol: Solicitud) -> list[dict]:
    """Recicladores de la zona con horario compatible, con su ventana y fechas posibles."""
    res = []
    for rec in s.scalars(select(PersonalCampo).where(PersonalCampo.tipo == "reciclador",
                                                     PersonalCampo.activo.is_(True)).order_by(PersonalCampo.nombre)):
        v = ventana(sol, rec)
        if v:
            res.append({"reciclador": rec, **v, "fechas": fechas_posibles(v)})
    return res


def asignar(s, sol: Solicitud, actor: Usuario, reciclador_id: int) -> Solicitud:
    """RN-03: la atención queda asociada al coordinador del flujo y a un reciclador de la zona
    cuyo horario coincide con el que eligió el usuario."""
    _exigir_coordinador(actor, sol)
    if sol.estado not in ("recibida", "en_revision", "asignada", "programada"):
        raise ErrorSolicitud(f"No se puede asignar una solicitud {sol.estado}")
    rec = s.get(PersonalCampo, reciclador_id)
    if not rec or rec.tipo != "reciclador" or not rec.activo:
        raise ErrorSolicitud("Solo se asignan recicladores activos")
    if not ventana(sol, rec):
        raise ErrorSolicitud("Ese reciclador no es de la zona o su horario no coincide con el del usuario")
    cambia = sol.reciclador_id != rec.id
    sol.coordinador_id, sol.reciclador_id = actor.id, rec.id
    if sol.estado != "asignada" and (cambia or sol.estado != "programada"):
        sol.fecha_programada = sol.hora_programada = None
        _cambiar_estado(s, sol, "asignada", actor, f"Asignada a {rec.nombre_completo}")
    elif cambia:
        _cambiar_estado(s, sol, "asignada", actor, f"Reasignada a {rec.nombre_completo}")
    s.flush()
    s.refresh(sol)
    return sol


def programar(s, sol: Solicitud, actor: Usuario, fecha: date, hora: time) -> Solicitud:
    """RN-02: solo queda programada con día, hora y persona encargada, dentro de la ventana."""
    _exigir_coordinador(actor, sol)
    if not sol.reciclador_id:
        raise ErrorSolicitud("Primero asigna el reciclador (RN-02)")
    if sol.estado not in ("asignada", "programada"):
        raise ErrorSolicitud(f"No se puede programar una solicitud {sol.estado}")
    v = ventana(sol, sol.reciclador)
    if not v:
        raise ErrorSolicitud("El reciclador asignado ya no coincide con la zona u horario del usuario")
    if fecha < date.today():
        raise ErrorSolicitud("La fecha ya pasó")
    if DIAS_SEMANA[fecha.weekday()] not in v["dias"]:
        raise ErrorSolicitud("Ese día no está disponible para el usuario o el reciclador")
    if not (v["desde"] <= hora < v["hasta"]):
        raise ErrorSolicitud(f"La hora debe estar entre {v['desde']:%H:%M} y {v['hasta']:%H:%M}")
    sol.fecha_programada, sol.hora_programada = fecha, hora
    _cambiar_estado(s, sol, "programada", actor, f"{fecha:%d/%m/%Y} {hora:%H:%M}")
    s.flush()
    s.refresh(sol)
    obtener_notificador().solicitud_programada(s, sol)
    return sol


def calcular_puntos(flujo: str, cantidad_kg: Decimal) -> tuple[int, str]:
    """RN-06: puntos = base + kg x factor del flujo (redondeo hacia abajo). Valores NO oficiales."""
    cfg = config()
    factor = cfg.puntos_kg_organico if flujo == "organico" else cfg.puntos_kg_reciclable
    puntos = cfg.puntos_base + math.floor(float(cantidad_kg) * factor)
    return puntos, f"{cfg.puntos_base} base + {cantidad_kg} kg x {factor} ({flujo}) = {puntos}"


def registrar_recoleccion(s, sol: Solicitud, actor: Usuario, cantidad_kg: Decimal,
                          observaciones: str | None = None) -> Recoleccion:
    """RN-05: los puntos solo se asignan al registrar la recolección. La registra la coordinación
    cuando el reciclador entrega en la huerta o el punto de acopio."""
    _exigir_coordinador(actor, sol)
    if sol.estado != "programada":
        raise ErrorSolicitud("Solo se registra la recolección de una solicitud programada")
    if cantidad_kg <= 0:
        raise ErrorSolicitud("La cantidad debe ser mayor que cero")
    puntos, regla = calcular_puntos(sol.flujo, cantidad_kg)
    rec = Recoleccion(solicitud_id=sol.id, registrado_por_id=actor.id, reciclador_id=sol.reciclador_id,
                      usuario_id=sol.usuario_id,
                      cantidad_kg=cantidad_kg, puntos=puntos, regla=regla, observaciones=observaciones)
    s.add(rec)
    _cambiar_estado(s, sol, "recolectada", actor, f"{cantidad_kg} kg, {puntos} puntos")
    return rec


def cancelar(s, sol: Solicitud, actor: Usuario, motivo: str | None = None) -> Solicitud:
    if not (actor.id == sol.usuario_id or _es_coordinador(actor, sol)):
        raise SinPermiso("Solo el solicitante o el coordinador pueden cancelar")
    if sol.estado in ("recolectada", "cancelada"):
        raise ErrorSolicitud(f"La solicitud ya está {sol.estado}")
    _cambiar_estado(s, sol, "cancelada", actor, motivo)
    return sol


def puntos_de(s, usuario_id: int) -> int:
    from sqlalchemy import func
    return s.scalar(select(func.coalesce(func.sum(Recoleccion.puntos), 0))
                    .where(Recoleccion.usuario_id == usuario_id)) or 0


def puntos_por_bonificacion(s, usuario_id: int) -> dict[str, int]:
    """Puntos separados según la bonificación elegida en cada solicitud. Las solicitudes antiguas
    sin bonificación cuentan como canje en tiendas."""
    from sqlalchemy import func
    tipo = func.coalesce(Solicitud.bonificacion, "tiendas")
    filas = s.execute(select(tipo, func.sum(Recoleccion.puntos))
                      .join(Solicitud, Solicitud.id == Recoleccion.solicitud_id)
                      .where(Recoleccion.usuario_id == usuario_id).group_by(tipo)).all()
    res = {b: 0 for b in BONIFICACIONES}
    res.update({b: int(p or 0) for b, p in filas})
    return res


# Insignias que crecen con los puntos (como una racha): la alcancía sube de nivel cada
# PASO_ALCANCIA puntos de tiendas y la trinitaria cada PASO_TRINITARIA puntos del huerto.
PASO_ALCANCIA, PASO_TRINITARIA, NIVEL_MAXIMO = 10, 5, 5


def _nivel(puntos: int, paso: int) -> dict:
    nivel = min(puntos // paso, NIVEL_MAXIMO)
    faltan = 0 if nivel == NIVEL_MAXIMO else paso - puntos % paso
    return {"puntos": puntos, "nivel": nivel, "nivel_maximo": NIVEL_MAXIMO, "paso": paso, "faltan": faltan}


def insignias(s, usuario_id: int) -> dict:
    p = puntos_por_bonificacion(s, usuario_id)
    return {"alcancia": _nivel(p["tiendas"], PASO_ALCANCIA), "trinitaria": _nivel(p["huerto"], PASO_TRINITARIA)}

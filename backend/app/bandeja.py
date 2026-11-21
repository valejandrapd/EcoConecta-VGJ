"""Bandeja web de notificaciones del solicitante.

- `asignada` y `programada` se crean cuando la coordinación actúa (y como respaldo al leer la bandeja).
- Recordatorios (mañana / hoy) y avisos de zona se generan al leer la bandeja: no hay procesos en
  segundo plano. La clave única evita duplicados.
- Los avisos de la propia solicitud que ya no coinciden con su estado actual se ocultan.
- RN-07: el aviso de zona no revela a quién se visita ni nombra al reciclador.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert

from .config import config
from .models import DireccionUsuario, Notificacion, Solicitud, Usuario

DIAS_ZONA = 7
RETENCION_DIAS = 30
NOMBRE_DIA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def _hoy() -> date:
    return datetime.now(ZoneInfo(config().zona_horaria)).date()


def _hora(h: time | None) -> str:
    if not h:
        return ""
    n = h.hour % 12 or 12
    m = f":{h.minute:02d}" if h.minute else ""
    if h.hour == 12 and not h.minute:
        return "12 m."
    return f"{n}{m} {'a. m.' if h.hour < 12 else 'p. m.'}"


def _dia(f: date) -> str:
    return f"{NOMBRE_DIA[f.weekday()]} {f:%d/%m}"


def _crear(s, usuario_id: int, tipo: str, clave: str, titulo: str, cuerpo: str, *,
           solicitud_id=None, accion=None, fecha_evento=None):
    s.execute(insert(Notificacion).values(
        usuario_id=usuario_id, tipo=tipo, clave=clave, titulo=titulo, cuerpo=cuerpo[:300],
        solicitud_id=solicitud_id, accion=accion, fecha_evento=fecha_evento,
        creada_en=datetime.now(timezone.utc)).on_conflict_do_nothing(index_elements=["clave"]))


# ------------------------------------------------------------ avisos de la propia solicitud
def _clave_asignada(sol: Solicitud) -> str:
    return f"asig:{sol.id}:{sol.reciclador_id}"


def _clave_programada(sol: Solicitud) -> str:
    return f"prog:{sol.id}:{sol.fecha_programada}:{sol.hora_programada}"


def avisar_asignada(s, sol: Solicitud):
    if not sol.reciclador:
        return
    _crear(s, sol.usuario_id, "asignada", _clave_asignada(sol), "Solicitud asignada",
           f"Tu solicitud {sol.codigo} fue asignada a {sol.reciclador.nombre_completo}. "
           "Pronto te diremos el día y la hora.", solicitud_id=sol.id)


def avisar_programada(s, sol: Solicitud):
    if not (sol.reciclador and sol.fecha_programada and sol.hora_programada):
        return
    _crear(s, sol.usuario_id, "programada", _clave_programada(sol), "Recolección programada",
           f"{sol.reciclador.nombre_completo} pasará por tu solicitud {sol.codigo} el "
           f"{_dia(sol.fecha_programada)} a las {_hora(sol.hora_programada)}.",
           solicitud_id=sol.id, fecha_evento=sol.fecha_programada)


def _vigente(n: Notificacion, hoy: date) -> bool:
    """¿El aviso sigue diciendo la verdad sobre su solicitud?"""
    if n.tipo == "zona":
        return True  # se revisa aparte
    sol = n.solicitud
    if sol is None:
        return False
    if n.tipo == "asignada":
        return n.clave == _clave_asignada(sol) and sol.estado in ("asignada", "programada", "recolectada")
    if n.tipo == "programada":
        return n.clave == _clave_programada(sol) and sol.estado in ("programada", "recolectada")
    if n.tipo in ("recordatorio_manana", "recordatorio_hoy"):
        return (sol.estado == "programada" and sol.fecha_programada == n.fecha_evento
                and n.fecha_evento is not None and n.fecha_evento >= hoy)
    return True


# ------------------------------------------------------------ generación al leer
def _zonas_de(s, u: Usuario) -> set[str]:
    zonas = {u.zona} if u.zona else set()
    zonas |= {z for z in s.scalars(select(DireccionUsuario.zona).where(DireccionUsuario.usuario_id == u.id)) if z}
    return zonas


def generar_pendientes(s, u: Usuario):
    if u.rol != "solicitante":
        return
    hoy = _hoy()
    s.execute(delete(Notificacion).where(
        Notificacion.usuario_id == u.id,
        Notificacion.creada_en < datetime.now(timezone.utc) - timedelta(days=RETENCION_DIAS)))

    propias = s.scalars(select(Solicitud).where(Solicitud.usuario_id == u.id,
                                               Solicitud.estado.in_(("asignada", "programada")))).all()
    for sol in propias:
        avisar_asignada(s, sol)  # respaldo: solicitudes asignadas antes de existir la bandeja
        if sol.estado != "programada" or not sol.fecha_programada:
            continue
        avisar_programada(s, sol)
        f, h = sol.fecha_programada, _hora(sol.hora_programada)
        if f == hoy + timedelta(days=1):
            _crear(s, u.id, "recordatorio_manana", f"rec1:{sol.id}:{f}", "Mañana pasan por tus residuos",
                   f"Mañana pasan por tu solicitud {sol.codigo} a las {h}. Ten listos tus residuos.",
                   solicitud_id=sol.id, fecha_evento=f)
        elif f == hoy:
            _crear(s, u.id, "recordatorio_hoy", f"rec0:{sol.id}:{f}", "Hoy pasan por tus residuos",
                   f"Hoy pasan por tu solicitud {sol.codigo} a las {h}. Ten listos tus residuos.",
                   solicitud_id=sol.id, fecha_evento=f)

    zonas = _zonas_de(s, u)
    if not zonas:
        return
    visitas = s.execute(select(Solicitud.reciclador_id, Solicitud.zona, Solicitud.fecha_programada,
                               Solicitud.hora_programada, Solicitud.usuario_id)
                        .where(Solicitud.estado == "programada", Solicitud.zona.in_(zonas),
                               Solicitud.reciclador_id.is_not(None),
                               Solicitud.fecha_programada.between(hoy, hoy + timedelta(days=DIAS_ZONA)))).all()
    grupos: dict[tuple, dict] = {}
    for rec_id, zona, f, h, dueno in visitas:
        g = grupos.setdefault((rec_id, zona, f), {"hora": h, "propia": False})
        if h and (not g["hora"] or h < g["hora"]):
            g["hora"] = h
        g["propia"] |= dueno == u.id
    for (rec_id, zona, f), g in grupos.items():
        if g["propia"]:
            continue  # ya recibió el aviso de su propia recolección
        cuando = "hoy" if f == hoy else "mañana" if f == hoy + timedelta(days=1) else f"el {_dia(f)}"
        _crear(s, u.id, "zona", f"zona:{u.id}:{rec_id}:{zona}:{f}", "Un reciclador pasará por tu zona",
               f"Un reciclador pasará por {zona} {cuando} desde las {_hora(g['hora'])}. "
               "¿Tienes residuos y estás libre a esa hora? Pide tu recolección.",
               accion="nueva_solicitud", fecha_evento=f)


def _zona_vigente(s, n: Notificacion, hoy: date) -> bool:
    if not n.fecha_evento or n.fecha_evento < hoy:
        return False
    _, _, rec_id, zona, _ = n.clave.split(":", 4)
    return s.scalar(select(Solicitud.id).where(
        Solicitud.estado == "programada", Solicitud.reciclador_id == int(rec_id), Solicitud.zona == zona,
        Solicitud.fecha_programada == n.fecha_evento).limit(1)) is not None


def visibles(s, u: Usuario) -> list[Notificacion]:
    if u.rol != "solicitante":
        return []
    generar_pendientes(s, u)
    s.flush()
    hoy = _hoy()
    todas = s.scalars(select(Notificacion).where(Notificacion.usuario_id == u.id)
                      .order_by(Notificacion.creada_en.desc(), Notificacion.id.desc())).all()
    return [n for n in todas if (_zona_vigente(s, n, hoy) if n.tipo == "zona" else _vigente(n, hoy))]


def marcar_leida(s, u: Usuario, notificacion_id: int) -> bool:
    n = s.get(Notificacion, notificacion_id)
    if not n or n.usuario_id != u.id:
        return False
    n.leida_en = n.leida_en or datetime.now(timezone.utc)
    return True


def marcar_todas(s, u: Usuario):
    s.execute(update(Notificacion).where(Notificacion.usuario_id == u.id, Notificacion.leida_en.is_(None))
              .values(leida_en=datetime.now(timezone.utc)))


def a_dict(n: Notificacion) -> dict:
    return {"id": n.id, "tipo": n.tipo, "titulo": n.titulo, "cuerpo": n.cuerpo,
            "codigo_solicitud": n.solicitud.codigo if n.solicitud else None, "accion": n.accion,
            "fecha_evento": n.fecha_evento, "leida": n.leida_en is not None, "creada_en": n.creada_en}

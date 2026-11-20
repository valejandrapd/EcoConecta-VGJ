"""Modelo de datos (PostgreSQL).

Supuesto: la especificación principal no está en el repositorio; los campos de `usuarios`,
`solicitudes` y `contenidos` son los mínimos que necesita el bot y se ajustarán a ella.
"""
from datetime import date, datetime, time, timezone

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, Sequence, String, Text, Time,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

FLUJOS = ("organico", "reciclable")
PREFIJO_FLUJO = {"organico": "ORG", "reciclable": "REC"}
ESTADOS_SOLICITUD = ("recibida", "programada", "completada", "cancelada")

SEQ_ORG = Sequence("seq_codigo_org", metadata=Base.metadata)
SEQ_REC = Sequence("seq_codigo_rec", metadata=Base.metadata)


def ahora():
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # E.164
    direccion: Mapped[str | None] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="ciudadano")  # ciudadano|coordinador|recolector
    flujo: Mapped[str | None] = mapped_column(String(20))  # flujo que coordina (organico|reciclable)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # ORG-0042 | REC-0017
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    flujo: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), default="recibida")
    descripcion: Mapped[str | None] = mapped_column(Text)
    direccion: Mapped[str | None] = mapped_column(String(255))
    fecha_programada: Mapped[date | None] = mapped_column(Date)
    hora_programada: Mapped[time | None] = mapped_column(Time)
    encargado_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)

    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    encargado: Mapped[Usuario | None] = relationship(foreign_keys=[encargado_id])


class Contenido(Base):
    """Información educativa. El bot SOLO responde con lo que haya aquí."""
    __tablename__ = "contenidos"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))  # tutorial | horario | ruta | general
    titulo: Mapped[str] = mapped_column(String(160))
    cuerpo: Mapped[str] = mapped_column(Text)
    palabras_clave: Mapped[str] = mapped_column(Text, default="")  # separadas por coma
    flujo: Mapped[str | None] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class MensajeWhatsapp(Base):
    """Registro mínimo de la conversación: sin texto libre ni fotos, solo metadatos."""
    __tablename__ = "mensajes_whatsapp"
    __table_args__ = (UniqueConstraint("wa_message_id", name="uq_mensajes_wa_message_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    wa_message_id: Mapped[str | None] = mapped_column(String(128))  # id de Meta (entrantes) -> evita duplicados
    wa_id: Mapped[str] = mapped_column(String(20), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    direccion: Mapped[str] = mapped_column(String(10))  # entrante | saliente
    tipo: Mapped[str] = mapped_column(String(12))  # texto | imagen | plantilla | otro
    intencion: Mapped[str | None] = mapped_column(String(40))  # menu, clasificar, estado, info, derivar...
    plantilla: Mapped[str | None] = mapped_column(String(60))
    estado_envio: Mapped[str | None] = mapped_column(String(20))  # enviado | fallido | log
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, index=True)
    retener_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ConversacionWhatsapp(Base):
    """Estado corto de cada número: ventana de 24 h, intentos fallidos y paso actual."""
    __tablename__ = "conversaciones_whatsapp"
    wa_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    estado: Mapped[str | None] = mapped_column(String(30))  # None | esperando_residuo
    fallos_seguidos: Mapped[int] = mapped_column(Integer, default=0)
    ultimo_flujo: Mapped[str | None] = mapped_column(String(20))
    ultimo_entrante_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aviso_limite_en: Mapped[date | None] = mapped_column(Date)


class CasoCoordinacion(Base):
    """Bandeja del coordinador: casos derivados desde el bot."""
    __tablename__ = "casos_coordinacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    flujo: Mapped[str] = mapped_column(String(20), index=True)  # organico | reciclable | general
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    canal: Mapped[str] = mapped_column(String(20), default="whatsapp")
    motivo: Mapped[str] = mapped_column(String(30))  # pidio_persona | no_entendido | sin_contenido
    resumen: Mapped[str | None] = mapped_column(String(300))
    estado: Mapped[str] = mapped_column(String(20), default="abierto")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    usuario: Mapped[Usuario | None] = relationship()

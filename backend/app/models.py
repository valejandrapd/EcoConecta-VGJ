"""Modelo de datos (PostgreSQL), alineado con el reto oficial (RN-01 a RN-08)."""
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Sequence, String, Text, Time,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

FLUJOS = ("organico", "reciclable")
PREFIJO_FLUJO = {"organico": "ORG", "reciclable": "REC"}
# RN-04: estados trazables (sección 5.4 del reto)
ESTADOS_SOLICITUD = ("recibida", "en_revision", "asignada", "programada", "recolectada", "cancelada")
TIPOS_GENERADOR = ("hogar", "unidad_productiva")
# Asistente de nueva solicitud (web)
TAMANOS = ("pequeno", "mediano", "grande")
DIAS_SEMANA = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
# Cómo quiere recibir el solicitante sus puntos: canje en tiendas de la zona o servicios del huerto
BONIFICACIONES = ("tiendas", "huerto")
# Perfiles con acceso a la web: solo estos cuatro. Cada coordinador atiende un flujo (RN-01).
ROLES = ("solicitante", "coordinador_huerta", "coordinador_reciclaje", "administrador")
FLUJO_DE_ROL = {"coordinador_huerta": "organico", "coordinador_reciclaje": "reciclable"}
COORDINADOR_DE_FLUJO = {"organico": "coordinador_huerta", "reciclable": "coordinador_reciclaje"}
# Personal de campo SIN cuenta: los registra la coordinación. Solo los recicladores recolectan
# (también los orgánicos); los voluntarios de huerta no recolectan.
TIPOS_PERSONAL = ("reciclador", "voluntario_huerta")

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
    zona: Mapped[str | None] = mapped_column(String(60))
    rol: Mapped[str] = mapped_column(String(30), default="solicitante")
    tipo_generador: Mapped[str | None] = mapped_column(String(20))  # hogar | unidad_productiva
    piloto: Mapped[bool] = mapped_column(Boolean, default=False)  # RN-08: habilitado en el piloto
    clave_hash: Mapped[str | None] = mapped_column(String(255))  # scrypt; nunca la clave en claro
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    @property
    def flujo(self) -> str | None:
        return FLUJO_DE_ROL.get(self.rol)


class PersonalCampo(Base):
    """Recicladores y voluntarios de huerta. No inician sesión: la coordinación les avisa por sus
    propios medios y registra todo en la web."""
    __tablename__ = "personal_campo"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)  # reciclador | voluntario_huerta
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))
    zona: Mapped[str | None] = mapped_column(String(60), index=True)  # solo recicladores
    dias_servicio: Mapped[str] = mapped_column(String(40))  # "lun,mar,sab"
    hora_desde: Mapped[time] = mapped_column(Time)
    hora_hasta: Mapped[time] = mapped_column(Time)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def dias(self) -> list[str]:
        return self.dias_servicio.split(",") if self.dias_servicio else []


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # ORG-0042 | REC-0017
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    flujo: Mapped[str] = mapped_column(String(20), index=True)  # RN-01
    tipo_generador: Mapped[str] = mapped_column(String(20), default="hogar")
    estado: Mapped[str] = mapped_column(String(20), default="recibida", index=True)
    observaciones: Mapped[str | None] = mapped_column(Text)
    direccion: Mapped[str | None] = mapped_column(String(255))
    zona: Mapped[str | None] = mapped_column(String(60), index=True)
    disponibilidad: Mapped[str | None] = mapped_column(String(120))  # texto legible de días y horario
    tamano: Mapped[str | None] = mapped_column(String(10))  # pequeno | mediano | grande
    dias_disponibles: Mapped[str | None] = mapped_column(String(40))  # "lun,mie,vie"
    hora_desde: Mapped[time | None] = mapped_column(Time)
    hora_hasta: Mapped[time | None] = mapped_column(Time)
    direccion_etiqueta: Mapped[str | None] = mapped_column(String(60))  # "Casa mamá"
    bonificacion: Mapped[str | None] = mapped_column(String(10))  # tiendas | huerto
    coordinador_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))  # RN-03
    reciclador_id: Mapped[int | None] = mapped_column(ForeignKey("personal_campo.id"))  # RN-03
    fecha_programada: Mapped[date | None] = mapped_column(Date)  # RN-02
    hora_programada: Mapped[time | None] = mapped_column(Time)   # RN-02
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)

    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    coordinador: Mapped[Usuario | None] = relationship(foreign_keys=[coordinador_id])
    reciclador: Mapped[PersonalCampo | None] = relationship()
    recoleccion: Mapped["Recoleccion | None"] = relationship(back_populates="solicitud", uselist=False)


class DireccionUsuario(Base):
    """Direcciones adicionales del solicitante, con una etiqueta propia ("Casa mamá")."""
    __tablename__ = "direcciones_usuario"
    __table_args__ = (UniqueConstraint("usuario_id", "etiqueta", name="uq_direccion_etiqueta"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    etiqueta: Mapped[str] = mapped_column(String(60))
    direccion: Mapped[str] = mapped_column(String(255))
    zona: Mapped[str | None] = mapped_column(String(60))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class HistorialSolicitud(Base):
    """RN-04: cada cambio de estado queda registrado con quién lo hizo."""
    __tablename__ = "historial_solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(20))
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    nota: Mapped[str | None] = mapped_column(String(300))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Recoleccion(Base):
    """RN-05/RN-06: la recolección registrada y los puntos calculados con la regla parametrizada."""
    __tablename__ = "recolecciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True)
    # Coordinador que registra la recolección (la columna conserva su nombre histórico)
    registrado_por_id: Mapped[int] = mapped_column("recolector_id", ForeignKey("usuarios.id"))
    reciclador_id: Mapped[int | None] = mapped_column(ForeignKey("personal_campo.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    cantidad_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    puntos: Mapped[int] = mapped_column(Integer)
    regla: Mapped[str] = mapped_column(String(200))  # cómo se calcularon (explicable)
    observaciones: Mapped[str | None] = mapped_column(Text)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    solicitud: Mapped[Solicitud] = relationship(back_populates="recoleccion")


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

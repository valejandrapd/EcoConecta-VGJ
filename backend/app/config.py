"""Configuración leída de variables de entorno. Los valores reales NUNCA van en el código."""
import os
from dataclasses import dataclass
from functools import lru_cache


def _int(nombre, defecto):
    try:
        return int(os.environ.get(nombre, defecto))
    except ValueError:
        return defecto


def _float(nombre, defecto):
    try:
        return float(os.environ.get(nombre, defecto))
    except ValueError:
        return defecto


@dataclass(frozen=True)
class Config:
    database_url: str
    zona_horaria: str
    pais_telefono: str
    # WhatsApp Business Cloud API (Meta)
    notificador: str  # "whatsapp" | "log"
    wa_token: str
    wa_phone_number_id: str
    wa_verify_token: str
    wa_app_secret: str
    graph_version: str
    graph_timeout_s: float
    plantilla_idioma: str
    plantilla_solicitud_recibida: str
    plantilla_nueva_solicitud: str
    plantilla_solicitud_programada: str
    # IA (Claude API)
    anthropic_api_key: str
    ia_modelo_texto: str
    ia_modelo_vision: str
    ia_timeout_s: float
    # Bot
    limite_mensajes_dia: int
    retencion_mensajes_dias: int
    url_formulario: str
    url_registro: str
    # API interna
    service_api_key: str
    auth_secret: str
    sesion_horas: int
    # RN-08: solo usuarios marcados como piloto usan los servicios
    modo_piloto: bool
    # RN-06: regla de puntos parametrizable (valores de ejemplo, NO oficiales de FSD)
    puntos_base: int
    puntos_kg_organico: float
    puntos_kg_reciclable: float

    @property
    def whatsapp_activo(self) -> bool:
        return self.notificador == "whatsapp" and bool(self.wa_token and self.wa_phone_number_id)


@lru_cache
def config() -> Config:
    modelo = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
    return Config(
        database_url=os.environ.get("DATABASE_URL", "postgresql+psycopg://ecoconecta:ecoconecta@localhost:5432/ecoconecta"),
        zona_horaria=os.environ.get("ZONA_HORARIA", "America/Bogota"),
        pais_telefono=os.environ.get("PAIS_TELEFONO", "57"),
        notificador=os.environ.get("NOTIFICADOR", "log").strip().lower(),
        wa_token=os.environ.get("WHATSAPP_TOKEN", ""),
        wa_phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
        wa_verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
        wa_app_secret=os.environ.get("WHATSAPP_APP_SECRET", ""),
        graph_version=os.environ.get("GRAPH_API_VERSION", "v21.0"),
        graph_timeout_s=_float("GRAPH_TIMEOUT_S", 10),
        plantilla_idioma=os.environ.get("WHATSAPP_PLANTILLA_IDIOMA", "es"),
        plantilla_solicitud_recibida=os.environ.get("PLANTILLA_SOLICITUD_RECIBIDA", "solicitud_recibida"),
        plantilla_nueva_solicitud=os.environ.get("PLANTILLA_NUEVA_SOLICITUD", "nueva_solicitud"),
        plantilla_solicitud_programada=os.environ.get("PLANTILLA_SOLICITUD_PROGRAMADA", "solicitud_programada"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        ia_modelo_texto=os.environ.get("IA_MODELO_TEXTO", modelo),
        ia_modelo_vision=os.environ.get("IA_MODELO_VISION", modelo),
        ia_timeout_s=_float("IA_TIMEOUT_S", 20),
        limite_mensajes_dia=_int("LIMITE_MENSAJES_DIA", 50),
        retencion_mensajes_dias=_int("RETENCION_MENSAJES_DIAS", 90),
        url_formulario=os.environ.get("URL_FORMULARIO_SOLICITUD", "http://localhost:3000/solicitudes/nueva"),
        url_registro=os.environ.get("URL_REGISTRO", "http://localhost:3000/registro"),
        service_api_key=os.environ.get("SERVICE_API_KEY", ""),
        auth_secret=os.environ.get("AUTH_SECRET", ""),
        sesion_horas=_int("SESION_HORAS", 12),
        modo_piloto=os.environ.get("MODO_PILOTO", "true").strip().lower() in {"1", "true", "si", "sí"},
        puntos_base=_int("PUNTOS_BASE_RECOLECCION", 5),
        puntos_kg_organico=_float("PUNTOS_POR_KG_ORGANICO", 2),
        puntos_kg_reciclable=_float("PUNTOS_POR_KG_RECICLABLE", 3),
    )

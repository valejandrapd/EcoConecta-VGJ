"""Varios residuos en un mismo mensaje: los separa y los agrupa por flujo.

Idea tomada del bot de `chatbot/segmentar.py` (otro integrante del equipo), adaptada a la
cascada de este backend: "tengo cáscaras de banano y hojas de papel" ->
{"organico": ["cáscaras de banano"], "reciclable": ["hojas de papel"], "otro": []}.

Cada parte pasa primero por las reglas; solo las que las reglas no deciden van al modelo
(Azure OpenAI o Claude, según IA_PROVEEDOR). La IA solo sugiere: la persona confirma.
"""
import logging
import re

from . import cascada
from .modelo import IANoDisponible

log = logging.getLogger("ecoconecta.ia")

_PREFIJO = re.compile(r"^\s*(?:hola[, ]+)?(?:tengo|tenemos|hay|quiero entregar|quiero|voy a entregar|"
                      r"vamos a entregar|necesito entregar|entregar)\s+(?:unas?|unos|algunas?|algunos|muchas?|muchos)?\s*",
                      re.I)
_SEPARADOR = re.compile(r"\s*(?:,|;|\by\b|\be\b|\bademás\b|\btambién\b|\bcon\b|\bmás\b)\s*", re.I)
MAX_PARTES = 6


def partes(texto: str) -> list[str]:
    salida = []
    for p in _SEPARADOR.split(_PREFIJO.sub("", texto or "")):
        p = p.strip(" .!¡¿?")
        if len(p) >= 3 and p not in salida:
            salida.append(p)
    return salida[:MAX_PARTES]


def agrupar(texto: str, usar_modelo: bool = True) -> dict[str, list[str]]:
    """Agrupa las partes del texto en organico / reciclable / otro."""
    grupos = {"organico": [], "reciclable": [], "otro": []}
    for p in partes(texto):
        sug = cascada.por_reglas(p)
        if (not sug or sug.categoria == "mezcla") and usar_modelo:
            try:
                sug = cascada.sugerir_texto(p)
            except IANoDisponible:
                sug = None
        cat = sug.categoria if sug else "desconocido"
        grupos[cat if cat in ("organico", "reciclable") else "otro"].append(p)
    return grupos


def es_mezcla(grupos: dict[str, list[str]]) -> bool:
    return bool(grupos["organico"] and grupos["reciclable"])

"""Segmenta lo que cuenta una persona (texto o transcripción de un audio) en residuos y los agrupa por tipo.

Ejemplo: "tengo cáscaras de banano y hojas de papel" ->
    [{"objeto": "cáscaras de banano", "categoria": "ORGANICO"}, {"objeto": "hojas de papel", "categoria": "RECICLABLE"}]
Cada tipo va a un colectivo distinto (ORGANICO -> huerteros, RECICLABLE -> recicladores), así que luego se crea
una solicitud por tipo. La IA solo SUGIERE: la persona confirma antes de que se cree nada.

Si hay ANTHROPIC_API_KEY se usa Claude (entiende frases libres); si no, o si falla, un separador por palabras clave.
"""
import json
import logging
import os
import re

from clasificador import clasificar_texto

log = logging.getLogger("ecoconecta")
CATEGORIAS = ("ORGANICO", "RECICLABLE", "OTRO", "DUDA")  # DUDA = no se pudo decidir; se le pregunta a la persona

PROMPT = (
    "Una persona de un barrio cuenta qué residuos quiere entregar. Sepáralos uno por uno y clasifica cada uno "
    "para separación en la fuente. Responde SOLO con un JSON: "
    '{"items": [{"objeto": "<nombre corto en español>", "categoria": "ORGANICO" | "RECICLABLE" | "OTRO" | "DUDA"}]}. '
    "ORGANICO = restos de comida, cáscaras, hojas y restos vegetales. "
    "RECICLABLE = plástico, vidrio, metal, papel y cartón limpios. "
    "OTRO = ni orgánico ni reciclable (higiénicos, mezclados, peligrosos). "
    "DUDA = no puedes decidirlo con lo dicho. Si no menciona ningún residuo, devuelve {\"items\": []}. "
    "No inventes residuos que no se mencionan. Texto de la persona: "
)

_PREFIJO = re.compile(r"^\s*(?:hola[, ]+)?(?:tengo|tenemos|hay|quiero entregar|quiero|voy a entregar|"
                      r"vamos a entregar|necesito entregar|entregar)\s+(?:unas?|unos|algunas?|algunos|muchas?|muchos)?\s*",
                      re.I)
_SEPARADOR = re.compile(r"\s*(?:,|;|\by\b|\be\b|\bademás\b|\badicional(?:mente)?\b|\btambién\b|\bcon\b|\bmás\b)\s*", re.I)


def segmentar_por_palabras(texto: str):
    """Separa por comas / "y" / "con"… y clasifica cada parte con el diccionario de palabras clave."""
    items = []
    for parte in _SEPARADOR.split(_PREFIJO.sub("", texto or "")):
        parte = parte.strip(" .!¡¿?")
        if len(parte) >= 3:
            items.append({"objeto": parte, "categoria": clasificar_texto(parte) or "DUDA"})
    return items


def interpretar(crudo: str):
    """Extrae la lista de ítems de la respuesta del modelo, tolerando texto extra o formatos raros."""
    m = re.search(r"\{.*\}", crudo or "", re.S)
    try:
        datos = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        datos = {}
    items = []
    for it in datos.get("items", []) if isinstance(datos, dict) else []:
        if not isinstance(it, dict):
            continue
        objeto = str(it.get("objeto", "")).strip()
        cat = str(it.get("categoria", "DUDA")).upper()
        if objeto:
            items.append({"objeto": objeto, "categoria": cat if cat in CATEGORIAS else "DUDA"})
    return items


def segmentar_con_claude(texto: str):
    import anthropic  # import perezoso: las pruebas y el modo sin clave no lo necesitan
    cliente = anthropic.Anthropic()
    r = cliente.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), max_tokens=400,
        messages=[{"role": "user", "content": PROMPT + json.dumps(texto, ensure_ascii=False)}])
    return interpretar("".join(b.text for b in r.content if b.type == "text"))


def segmentar_texto(texto: str):
    """Devuelve [{"objeto", "categoria"}]. Claude si hay clave; si falla, el separador por palabras clave."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return segmentar_con_claude(texto)
        except Exception:  # noqa: BLE001 - sin red, sin saldo, etc.: se sigue con el método local
            log.exception("Claude no pudo segmentar el texto; uso palabras clave")
    return segmentar_por_palabras(texto)


def agrupar(items):
    """{"ORGANICO": [objetos], "RECICLABLE": [...], "OTRO": [...], "DUDA": [...]} sin repetir objetos."""
    grupos = {c: [] for c in CATEGORIAS}
    for it in items:
        if it["objeto"] not in grupos[it["categoria"]]:
            grupos[it["categoria"]].append(it["objeto"])
    return grupos

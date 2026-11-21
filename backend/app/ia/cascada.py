"""Cascada de IA: 1) reglas, 2) modelo con texto, 3) modelo con visión.

Devuelve una `Sugerencia`; quien la usa (el bot o la web) decide qué mostrar.
La IA nunca crea, asigna, programa ni cierra solicitudes.
"""
from dataclasses import dataclass

from . import imagen, modelo, reglas

MAPA = {"ORGANICO": "organico", "RECICLABLE": "reciclable", "MEZCLA": "mezcla",
        "NO_APROVECHABLE": "no_aprovechable", "DESCONOCIDO": "desconocido"}


@dataclass
class Sugerencia:
    categoria: str  # organico | reciclable | mezcla | no_aprovechable | desconocido
    confianza: str  # alta | media | baja
    origen: str     # reglas | modelo_texto | modelo_vision
    objeto: str = ""

    @property
    def flujos(self) -> list[str]:
        if self.categoria == "mezcla":
            return ["organico", "reciclable"]
        return [self.categoria] if self.categoria in ("organico", "reciclable") else []


def por_reglas(texto: str) -> Sugerencia | None:
    p = reglas.puntuar(texto)
    org, rec = p["organico"], p["reciclable"]
    if org and rec:
        return Sugerencia("mezcla", "media", "reglas")
    if org or rec:
        total = org or rec
        return Sugerencia("organico" if org else "reciclable", "alta" if total >= 2 else "media", "reglas")
    return None


def _desde_modelo(r: dict, origen: str) -> Sugerencia:
    return Sugerencia(MAPA[r["categoria"]], r["confianza"], origen, r.get("objeto", ""))


def sugerir_texto(texto: str) -> Sugerencia:
    """Reglas primero; si no deciden, modelo con texto. Puede lanzar modelo.IANoDisponible."""
    s = por_reglas(texto)
    if s:
        return s
    return _desde_modelo(modelo.clasificar_texto(texto), "modelo_texto")


def sugerir_imagen(datos: bytes) -> Sugerencia:
    """Limpia la foto (sin EXIF, <=1024 px) y usa el modelo con visión. No guarda la foto."""
    jpeg = imagen.preparar(datos)
    return _desde_modelo(modelo.clasificar_imagen(jpeg), "modelo_vision")

"""Clasificador de residuos por texto: ORGANICO / RECICLABLE / None (no se sabe)."""
import re
import unicodedata

ORGANICO = "ORGANICO"
RECICLABLE = "RECICLABLE"

# Palabras clave por categoría (se comparan sin tildes y en minúscula).
PALABRAS = {
    ORGANICO: [
        "cascara", "cascaras", "fruta", "frutas", "verdura", "verduras", "hortaliza",
        "banano", "platano", "naranja", "manzana", "papa", "yuca", "tomate", "cebolla",
        "zanahoria", "lechuga", "aguacate", "limon", "mango", "piña", "sandia",
        "comida", "sobras", "restos de comida", "huevo", "cascara de huevo",
        "cafe", "borra de cafe", "bolsa de te", "te", "hojas", "hojas secas", "ramas",
        "cesped", "poda", "flores", "semillas", "pan", "arroz", "pasta", "carne",
        "hueso", "huesos", "pescado", "pollo", "servilleta usada",
    ],
    RECICLABLE: [
        "plastico", "botella", "botella de plastico", "pet", "envase", "envases", "lata",
        "latas", "aluminio", "vidrio", "frasco", "frascos", "tarro", "carton", "papel",
        "periodico", "revista", "revistas", "cuaderno", "cuadernos", "caja", "cajas",
        "bolsa plastica", "tapa", "tapas", "tetrapak", "tetra pak", "metal", "chatarra",
        "hojas de papel", "sobre", "libro", "libros", "tarro de vidrio", "cd",
    ],
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]+", " ", texto).strip()


def clasificar_texto(texto: str):
    """Devuelve ORGANICO, RECICLABLE o None si no está claro o hay empate."""
    t = f" {normalizar(texto)} "
    puntos = {ORGANICO: 0, RECICLABLE: 0}
    for categoria, palabras in PALABRAS.items():
        for p in palabras:
            if f" {normalizar(p)} " in t:
                # las frases largas pesan más que las palabras sueltas
                puntos[categoria] += len(p.split())
    if puntos[ORGANICO] == puntos[RECICLABLE]:
        return None
    return ORGANICO if puntos[ORGANICO] > puntos[RECICLABLE] else RECICLABLE

"""Paso 1 de la cascada: reglas por palabras clave (sin IA, sin costo).

Vocabulario tomado del clasificador original del bot (`chatbot/clasificador.py`).
"""
import re
import unicodedata

PALABRAS = {
    "organico": [
        "cascara", "cascaras", "fruta", "frutas", "verdura", "verduras", "hortaliza",
        "banano", "platano", "naranja", "manzana", "papa", "yuca", "tomate", "cebolla",
        "zanahoria", "lechuga", "aguacate", "limon", "mango", "piña", "sandia",
        "comida", "sobras", "restos de comida", "huevo", "cascara de huevo",
        "cafe", "borra de cafe", "bolsa de te", "hojas", "hojas secas", "ramas",
        "cesped", "poda", "flores", "semillas", "pan", "arroz", "pasta", "carne",
        "hueso", "huesos", "pescado", "pollo",
    ],
    "reciclable": [
        "plastico", "botella", "botellas", "botella de plastico", "pet", "envase", "envases", "lata",
        "latas", "aluminio", "vidrio", "frasco", "frascos", "tarro", "carton", "papel",
        "periodico", "revista", "revistas", "cuaderno", "cuadernos", "caja", "cajas",
        "bolsa plastica", "tapa", "tapas", "tetrapak", "tetra pak", "metal", "chatarra",
        "hojas de papel", "sobre", "libro", "libros", "tarro de vidrio",
    ],
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]+", " ", texto).strip()


def puntuar(texto: str) -> dict:
    """Puntos por flujo; las frases largas pesan más que las palabras sueltas."""
    t = f" {normalizar(texto)} "
    puntos = {"organico": 0, "reciclable": 0}
    for flujo, palabras in PALABRAS.items():
        for p in palabras:
            if f" {normalizar(p)} " in t:
                puntos[flujo] += len(p.split())
    # "hojas de papel" no debe sumar a "hojas" orgánicas
    if " hojas de papel " in t and puntos["organico"]:
        puntos["organico"] -= 1
    return puntos

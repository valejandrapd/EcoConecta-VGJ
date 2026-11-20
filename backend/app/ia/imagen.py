"""Preparación de fotos antes de enviarlas a la IA: sin EXIF y máximo 1024 px. Nunca se guardan."""
import io

from PIL import Image, ImageOps

LADO_MAXIMO = 1024


class ImagenInvalida(ValueError):
    pass


def preparar(datos: bytes) -> bytes:
    """Devuelve un JPEG nuevo (sin metadatos EXIF/GPS), con el lado mayor <= 1024 px."""
    try:
        img = Image.open(io.BytesIO(datos))
        img = ImageOps.exif_transpose(img)  # respeta la orientación antes de descartar el EXIF
        img = img.convert("RGB")
    except Exception as e:  # noqa: BLE001
        raise ImagenInvalida("No se pudo leer la imagen") from e
    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    limpia = Image.new("RGB", img.size)
    limpia.paste(img)  # copia solo los píxeles: no arrastra info/EXIF
    salida = io.BytesIO()
    limpia.save(salida, format="JPEG", quality=85)
    return salida.getvalue()

"""Cargas simuladas del webhook de Meta: verificación, texto, imagen, firma inválida y duplicado."""
from sqlalchemy import func, select

from app.db import sesion
from app.ia import modelo
from app.models import MensajeWhatsapp

from .conftest import ANA, EXTRANO, jpeg_con_exif, mensaje, publicar


def test_verificacion_get_ok(client):
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verificar-prueba",
                                       "hub.challenge": "1234"})
    assert r.status_code == 200 and r.text == "1234"


def test_verificacion_get_token_malo(client):
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1"})
    assert r.status_code == 403


def test_firma_invalida_se_rechaza(client, wa):
    r = publicar(client, mensaje(ANA, texto="hola"), secreto="otro-secreto")
    assert r.status_code == 403
    assert wa.enviados == []
    with sesion() as s:
        assert s.scalar(select(func.count()).select_from(MensajeWhatsapp)) == 0


def test_sin_firma_se_rechaza(client):
    r = client.post("/webhook", json=mensaje(ANA))
    assert r.status_code == 403


def test_texto_hola_responde_menu(client, wa):
    r = publicar(client, mensaje(ANA, texto="Hola"))
    assert r.status_code == 200
    (texto,) = wa.textos_a(ANA)
    assert "EcoConecta" in texto and "Consultar una solicitud" in texto
    with sesion() as s:
        dirs = sorted(m.direccion for m in s.scalars(select(MensajeWhatsapp)))
    assert dirs == ["entrante", "saliente"]


def test_texto_clasifica_por_reglas_sin_ia(client, wa):
    publicar(client, mensaje(ANA, texto="¿dónde boto las cáscaras de banano?"))
    (texto,) = wa.textos_a(ANA)
    assert "Orgánico" in texto and "confianza" in texto and "flujo=organico" in texto


def test_mezcla_sugiere_dos_solicitudes(client, wa):
    publicar(client, mensaje(ANA, texto="tengo sobras de comida con una botella de plástico"))
    (texto,) = wa.textos_a(ANA)
    assert "dos solicitudes" in texto and "flujo=organico" in texto and "flujo=reciclable" in texto


def test_imagen_usa_vision_con_foto_limpia(client, wa, monkeypatch):
    wa.media = jpeg_con_exif()
    vista = {}

    def vision_falsa(jpeg):
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(jpeg))
        vista["tam"], vista["exif"] = img.size, dict(img.getexif())
        return {"categoria": "RECICLABLE", "objeto": "botella", "confianza": "alta"}

    monkeypatch.setattr(modelo, "clasificar_imagen", vision_falsa)
    r = publicar(client, mensaje(ANA, tipo="image"))
    assert r.status_code == 200
    assert max(vista["tam"]) <= 1024 and vista["exif"] == {}
    (texto,) = wa.textos_a(ANA)
    assert "Reciclable" in texto and "alta" in texto and "flujo=reciclable" in texto


def test_ia_no_disponible_da_contingencia(client, wa, monkeypatch):
    wa.media = jpeg_con_exif(100, 100)

    def falla(_):
        raise modelo.IANoDisponible("timeout")

    monkeypatch.setattr(modelo, "clasificar_imagen", falla)
    publicar(client, mensaje(ANA, tipo="image"))
    (texto,) = wa.textos_a(ANA)
    assert "No pude analizar" in texto


def test_duplicado_se_descarta(client, wa):
    carga = mensaje(ANA, texto="hola", wamid="wamid.REPETIDO")
    r1 = publicar(client, carga)
    r2 = publicar(client, carga)  # Meta reintenta el mismo mensaje
    assert r1.json()["nuevos"] == 1 and r2.json()["duplicados"] == 1
    assert len(wa.textos_a(ANA)) == 1
    with sesion() as s:
        n = s.scalar(select(func.count()).select_from(MensajeWhatsapp).where(
            MensajeWhatsapp.wa_message_id == "wamid.REPETIDO"))
    assert n == 1


def test_no_registrado_solo_info_general(client, wa):
    publicar(client, mensaje(EXTRANO, texto="3"))
    (texto,) = wa.textos_a(EXTRANO)
    assert "no está registrado" in texto and "registro" in texto


def test_no_registrado_no_usa_ia_con_fotos(client, wa, monkeypatch):
    llamado = []
    monkeypatch.setattr(modelo, "clasificar_imagen", lambda j: llamado.append(1))
    publicar(client, mensaje(EXTRANO, tipo="image"))
    assert llamado == [] and "no está registrado" in wa.textos_a(EXTRANO)[0]


def test_limite_diario(client, wa):
    for _ in range(7):  # LIMITE_MENSAJES_DIA=5 en pruebas
        publicar(client, mensaje(ANA, texto="hola"))
    textos = wa.textos_a(ANA)
    assert len(textos) == 6  # 5 respuestas + 1 solo aviso de límite
    assert "límite" in textos[-1]

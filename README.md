# EcoConecta-VGJ · Chatbot de WhatsApp

Chatbot de **EcoConecta · Villas de San Pablo** (Hackathon Unilibre · Fundación Santo Domingo). Guía a hogares y
unidades productivas por WhatsApp para **solicitar la recolección** de sus residuos: identifica si son **orgánicos**
(→ huerteros) o **reciclables** (→ recicladores), registra la solicitud con un **identificador único**, avisa cuando se
**programa** (día, hora y persona) y cuando se **recolecta**, y muestra los **puntos** del usuario.

```
WhatsApp (Whapi) ─► bot.py ─► conversacion.py ─┐
App / Web ───────► api.py  ──────────────────────┼─► backend.py ─► core.py (provisional) ─► PostgreSQL
                                                   └─► BACKEND_URL  (backend real del equipo, ver docs/CONTRATO_BACKEND.md)
Foto ─► vision.py (Claude)   Audio ─► transcripcion.py (STT) ─► texto   Texto ─► segmentar.py (Claude)
```

> **Estado:** el chatbot está completo. Para la demostración incluye un **backend provisional** (`core.py`) que el
> equipo reemplazará por el real sin tocar el bot: ver [`docs/CONTRATO_BACKEND.md`](docs/CONTRATO_BACKEND.md).
> WhatsApp va por **Whapi.Cloud** como sustituto de la API de Meta (autorizado por la organización para este proyecto).

## Cómo conversa

`menú` en cualquier momento. Opciones: **1** Solicitar recolección · **2** Consultar mis solicitudes · **3** Ver mis puntos ·
**4** Aprender a separar · **5** ¿Qué residuo es?

Solicitar: tipo de generador → residuo (**texto, audio 🎙️ o foto 📷**) → *la persona confirma el tipo* → dirección →
disponibilidad → observaciones → resumen y confirmación → código `RES-AAAAMMDD-NNNN`.

**Varios residuos a la vez:** si dice _"tengo cáscaras de banano y hojas de papel"_ (escrito, en audio o en una foto con
ambos), el bot los **separa por tipo** y, al confirmar, crea **una solicitud por colectivo** (cáscaras → huerteros, papel →
recicladores) con la misma dirección y horario. Lo que no se pueda clasificar se le pregunta a la persona; lo no
aprovechable (ordinario) no genera solicitud. Los audios se transcriben y el bot responde _"🎙️ Entendí: «…»"_ para que
la persona verifique. Los audios necesitan `STT_API_KEY` (ver variables); sin ella el bot pide texto o foto.

## Ejecutar con Docker

```bash
cp chatbot/.env.example .env      # completa WHAPI_TOKEN, ANTHROPIC_API_KEY y POSTGRES_PASSWORD
docker compose up --build         # PostgreSQL + chatbot en http://localhost:5000
```

Para recibir WhatsApp desde tu PC: `ngrok http 5000` y en **Whapi.Cloud → Webhooks** agrega
`https://TU-URL.ngrok-free.app/webhook` (evento **messages · post**). En la nube, usa la URL pública del despliegue.

Sin Docker: `cd chatbot && pip install -r requirements.txt && DATABASE_URL=postgresql://… python app.py`.
Pruebas (necesitan una base PostgreSQL de pruebas, se borran sus tablas): `cd chatbot && TEST_DATABASE_URL=postgresql://… python -m pytest`.

## Variables de entorno (sin valores; ver `chatbot/.env.example`)

`WHAPI_TOKEN`, `ANTHROPIC_API_KEY`, `POSTGRES_PASSWORD`/`DATABASE_URL`; opcionales: `PILOTO_NUMEROS` (usuarios piloto, RN-08),
`PUNTOS_BASE`/`PUNTOS_POR_KG` (regla de puntos de demostración, **no oficial**), `BACKEND_URL`/`BACKEND_API_KEY`
(backend real), `STT_API_KEY`/`STT_URL`/`STT_MODEL`/`STT_LANGUAGE` (transcripción de audios), `API_KEY`, `CORS_ORIGINS`,
`MAX_FOTO_MB`, `CLAUDE_MODEL`, `PORT`.

## Uso de IA (punto 9 del reto)

- **Qué hace:** identifica los residuos de una **foto** (`vision.py`) o de lo que la persona cuenta (`segmentar.py`) con Claude y sugiere orgánico/reciclable para cada uno. Sin `ANTHROPIC_API_KEY`, el texto se separa y clasifica con palabras clave.
- **Datos enviados:** a Claude, solo la imagen o la frase sobre los residuos; a la API de transcripción, el **audio** de la persona (puede contener su voz). Nunca nombre, teléfono ni dirección. Avisar de esto en la política de datos.
- **Controles:** la persona confirma o corrige el tipo antes de crear la solicitud; el coordinador revisa; si la foto no se ve, se pide otra; la IA **no** asigna, programa ni cierra.

## API REST

`/api/v1` sirve al bot, a una app o a una web y es el contrato del backend: ver [`docs/API.md`](docs/API.md) y
[`docs/CONTRATO_BACKEND.md`](docs/CONTRATO_BACKEND.md).

## Archivos (`chatbot/`)

| Archivo | Qué hace |
|---|---|
| `app.py` | Servidor Flask: webhook `/webhook`, API `/api/v1` y `/health` |
| `bot.py` | Adaptador de WhatsApp (Whapi) ⇄ conversación |
| `conversacion.py` | Flujo paso a paso del chat, piloto y privacidad |
| `core.py` | **Backend provisional**: reglas RN-01…RN-06, estados, historial, puntos |
| `backend.py` | Elige backend provisional o real (`BACKEND_URL`) |
| `notificar.py` | Avisos por WhatsApp (recibida, asignada, programada, recolectada, cancelada) |
| `api.py` | API REST `/api/v1` |
| `db.py` | PostgreSQL con SQLAlchemy (solicitudes, historial, conversaciones) |
| `clasificador.py`, `segmentar.py`, `vision.py` | Clasificación por palabras clave, separación de varios residuos y foto (Claude) |
| `transcripcion.py` | Audio → texto (API compatible con OpenAI/Groq Whisper) |
| `contenido.py` | Contenido educativo de ejemplo (lo reemplaza el del administrador) |
| `whapi.py` | Enviar mensajes y descargar imágenes y audios de Whapi |
| `test_*.py` | Pruebas automáticas (74) |

## Límites conocidos

- El canal de prueba de Whapi tiene límites (150 mensajes, 5 chats distintos) y es una conexión no oficial.
- La regla de puntos y el contenido educativo son de demostración hasta que los valide la Fundación.
- La construcción de la imagen Docker no se pudo probar en el entorno de desarrollo (no había motor Docker); sí se probó la instalación de dependencias en un entorno limpio y la ejecución contra PostgreSQL.
- Nunca subas el archivo `.env`.

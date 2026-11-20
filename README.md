# EcoConecta-VGJ

Aplicativo de gestión de residuos. Este repositorio incluye el **clasificador de residuos** (`/chatbot`) que
identifica si un residuo es **orgánico** o **reciclable**, listo para usarse desde **WhatsApp**, una **app** o una **web**.

```
WhatsApp ─► bot.py ─┐
App / Web ─► api.py ─┴─► core.py ─► clasificador.py (texto) · vision.py (foto, Claude) ─► db.py (SQLite)
```

El núcleo (`core.py`) no depende de ningún canal: WhatsApp es solo un adaptador. Para integrarlo con tu app o web
usa la **API REST** — ver [`docs/API.md`](docs/API.md).

## Cómo funciona el chatbot

1. La persona escribe por WhatsApp qué residuo tiene → se crea una solicitud con **ID único** (`RES-AAAAMMDD-NNNN`).
2. Si el texto alcanza, responde **ORGÁNICO** o **RECICLABLE**.
3. Si no se sabe qué residuo es, **pide una foto** y lo identifica **por cámara** (API de Claude).
   La foto resuelve la misma solicitud, con el mismo ID.
4. Consulta de una solicitud: `estado RES-20261120-0001`.

Todo se guarda en SQLite (`chatbot/solicitudes.db`, tabla `solicitudes`) para que el resto del aplicativo
pueda leerlo: `codigo, contacto, canal, descripcion, categoria (ORGANICO|RECICLABLE|OTRO), objeto, metodo (texto|foto), estado, creada`.
`contacto` es el teléfono (WhatsApp) o el id de usuario de tu app; `canal` indica por dónde llegó.

## Puesta en marcha

```bash
cd chatbot
pip install -r requirements.txt
cp .env.example .env        # y completa WHAPI_TOKEN y ANTHROPIC_API_KEY
python -m pytest            # pruebas
python app.py               # servidor en http://localhost:5000 (webhook + API REST)
```

Para recibir mensajes en tu PC:

```bash
ngrok http 5000
```

En el panel de **Whapi.Cloud → tu canal → Webhooks** agrega `https://TU-URL.ngrok-free.app/webhook`
con el evento **messages · post**.

## Archivos

| Archivo | Qué hace |
|---|---|
| `chatbot/app.py` | Servidor Flask: webhook `/webhook`, API `/api/v1` y `/health` |
| `chatbot/core.py` | **Núcleo independiente del canal** (ID único, texto → foto) |
| `chatbot/api.py` | API REST para apps y webs (API key y CORS opcionales) |
| `chatbot/bot.py` | Adaptador de WhatsApp: mensajes de Whapi ⇄ `core` |
| `chatbot/clasificador.py` | Clasificación por texto (palabras clave, editables en `PALABRAS`) |
| `chatbot/vision.py` | Identificación por foto con la API de Claude |
| `chatbot/whapi.py` | Enviar mensajes y descargar imágenes de Whapi.Cloud |
| `chatbot/db.py` | Base de datos de solicitudes |
| `chatbot/test_bot.py`, `test_api.py` | Pruebas automáticas |

## Notas

- Nunca subas el archivo `.env` (ya está en `.gitignore`).
- El canal de prueba de Whapi tiene límites (150 mensajes, 5 chats distintos y una duración de 5 días).
- Para ampliar el vocabulario del clasificador de texto, agrega palabras en `PALABRAS` de `clasificador.py`.

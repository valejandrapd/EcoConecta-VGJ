# EcoConecta-VGJ

Aplicativo de gestión de residuos. Este repositorio incluye el **chatbot de WhatsApp** (`/chatbot`) que
identifica si un residuo es **orgánico** o **reciclable**.

## Cómo funciona el chatbot

1. La persona escribe por WhatsApp qué residuo tiene → se crea una solicitud con **ID único** (`RES-AAAAMMDD-NNNN`).
2. Si el texto alcanza, responde **ORGÁNICO** o **RECICLABLE**.
3. Si no se sabe qué residuo es, **pide una foto** y lo identifica **por cámara** (API de Claude).
   La foto resuelve la misma solicitud, con el mismo ID.
4. Consulta de una solicitud: `estado RES-20261120-0001`.

Todo se guarda en SQLite (`chatbot/solicitudes.db`, tabla `solicitudes`) para que el resto del aplicativo
pueda leerlo: `codigo, telefono, descripcion, categoria (ORGANICO|RECICLABLE|OTRO), metodo (texto|foto), estado, creada`.

## Puesta en marcha

```bash
cd chatbot
pip install -r requirements.txt
cp .env.example .env        # y completa WHAPI_TOKEN y ANTHROPIC_API_KEY
python -m pytest            # pruebas
python app.py               # servidor en http://localhost:5000
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
| `chatbot/app.py` | Servidor Flask con el webhook `/webhook` y `/health` |
| `chatbot/bot.py` | Lógica de la conversación (ID único, texto → foto) |
| `chatbot/clasificador.py` | Clasificación por texto (palabras clave, editables en `PALABRAS`) |
| `chatbot/vision.py` | Identificación por foto con la API de Claude |
| `chatbot/whapi.py` | Enviar mensajes y descargar imágenes de Whapi.Cloud |
| `chatbot/db.py` | Base de datos de solicitudes |
| `chatbot/test_bot.py` | Pruebas automáticas |

## Notas

- Nunca subas el archivo `.env` (ya está en `.gitignore`).
- El canal de prueba de Whapi tiene límites (150 mensajes, 5 chats distintos y una duración de 5 días).
- Para ampliar el vocabulario del clasificador de texto, agrega palabras en `PALABRAS` de `clasificador.py`.

# EcoConecta-VGJ

Aplicativo de gestión de residuos orgánicos y reciclables con un chatbot de WhatsApp.

- **Backend:** Python, FastAPI y PostgreSQL (`backend/`).
- **Canal:** WhatsApp Business Cloud API oficial de Meta (`backend/app/whatsapp/`).
- **IA:** Claude API, en cascada: reglas, luego modelo con texto, luego modelo con visión (`backend/app/ia/`).
- **Legado:** `chatbot/` es el bot original (Flask, Whapi.Cloud y SQLite). Se conserva como referencia y no se despliega (ver "Decisión de integración").

## Arquitectura

```mermaid
flowchart LR
    U[Persona en WhatsApp] -- mensaje / foto --> META[WhatsApp Business Cloud API]
    META -- "POST /webhook (firma X-Hub-Signature-256)" --> WH
    subgraph backend [backend FastAPI]
        WH[whatsapp/webhook] -- BackgroundTasks --> BOT[whatsapp/bot]
        BOT --> IA[ia/cascada]
        BOT --> MSJ[whatsapp/mensajeria]
        NOT[notificaciones] --> MSJ
        API[api/rutas] --> SOL[solicitudes] --> NOT
        MSJ --> CLI[whatsapp/cliente]
    end
    IA -- texto o foto limpia --> CLAUDE[Claude API]
    CLI -- Graph API --> META
    WEB[Web / formulario] -- "X-Service-Key" --> API
    backend --> PG[(PostgreSQL)]
```

Hay un solo webhook (`/webhook`) y un solo cliente de WhatsApp (`whatsapp/cliente.py`), que comparten el bot y las notificaciones del sistema. Más detalle en [`docs/arquitectura.md`](docs/arquitectura.md).

## Puesta en marcha

```bash
cp .env.example .env          # completa los valores (nunca subas el .env)
docker compose up --build     # PostgreSQL + backend en http://localhost:8000
docker compose exec backend python -m app.seed   # datos de demostración (opcional)
```

Sin Docker:

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/ecoconecta
uvicorn app.main:app --reload
```

Las tablas se crean al arrancar el backend.

### Pruebas

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/ecoconecta_test python -m pytest
```

Las pruebas usan PostgreSQL real. Simulan Meta y Claude, así que no necesitan credenciales.

## Chatbot de WhatsApp

### Qué hace

| Función | Estado |
|---|---|
| Menú de bienvenida en español (`hola`, `menú`) | Implementado |
| ¿Orgánico o reciclable? Por texto y por foto. Responde con sugerencia, confianza (alta, media o baja) y enlace al formulario. Si hay mezcla, sugiere dos solicitudes | Implementado. La IA solo sugiere y nunca crea ni modifica solicitudes |
| Consulta de estado por código (`ORG-0042`, `REC-0017`), solo para el número dueño de la solicitud (RN-07) | Implementado |
| Información educativa (tutorial, horarios, rutas), solo desde la tabla `contenidos` | Implementado |
| Derivación a una persona (lo pide el usuario, o el bot no entiende dos veces seguidas). Registra el caso en la bandeja del coordinador del flujo | Implementado (`casos_coordinacion`, `GET /api/bandeja`) |
| Notificaciones `solicitud_recibida`, `nueva_solicitud` y `solicitud_programada` | Implementado. Envía texto dentro de la ventana de 24 h y plantilla fuera de ella |
| Crear la solicitud completa por chat | Pendiente (opcional). Por ahora el bot envía el enlace al formulario web |

### Configuración en Meta

1. En [developers.facebook.com](https://developers.facebook.com) crea una app de tipo Business y agrega el producto **WhatsApp**.
2. Copia el *Phone number ID* y un token de acceso en `WHATSAPP_PHONE_NUMBER_ID` y `WHATSAPP_TOKEN`. Para producción usa un token de usuario del sistema; el token temporal vence en 24 h.
3. En *Configuración de la app → Básica* copia la *clave secreta de la app* en `WHATSAPP_APP_SECRET`. Con ella se valida `X-Hub-Signature-256`.
4. Inventa un valor para `WHATSAPP_VERIFY_TOKEN`.
5. En *WhatsApp → Configuración → Webhook* pon la URL de callback `https://<tu-dominio>/webhook` y el mismo verify token, y suscríbete al campo **messages**. En local puedes exponer el puerto con `ngrok http 8000`.
6. Crea y haz aprobar las plantillas `solicitud_recibida` ({{1}} = código), `nueva_solicitud` ({{1}} = código) y `solicitud_programada` ({{1}} = código, {{2}} = fecha, {{3}} = hora, {{4}} = encargado).
7. Pon `NOTIFICADOR=whatsapp`.

### Variables de entorno

Todas están documentadas en [`.env.example`](.env.example). Ninguna lleva valores en el repositorio.

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL |
| `NOTIFICADOR` | `whatsapp` (Graph API) o `log` (sin credenciales; usa `LogNotificador` y solo escribe en el log) |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | Envío por la Graph API |
| `WHATSAPP_VERIFY_TOKEN` | Verificación `GET /webhook` |
| `WHATSAPP_APP_SECRET` | Firma `X-Hub-Signature-256`. Si falta, se rechazan todos los POST |
| `GRAPH_API_VERSION`, `GRAPH_TIMEOUT_S` | Versión y tiempo máximo de espera de la Graph API |
| `PLANTILLA_*`, `WHATSAPP_PLANTILLA_IDIOMA` | Nombres e idioma de las plantillas aprobadas |
| `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `IA_MODELO_TEXTO`, `IA_MODELO_VISION`, `IA_TIMEOUT_S` | Claude API |
| `LIMITE_MENSAJES_DIA` | Máximo de mensajes por número al día (control de abuso) |
| `RETENCION_MENSAJES_DIAS` | Días que se conservan los registros de `mensajes_whatsapp` |
| `URL_FORMULARIO_SOLICITUD`, `URL_REGISTRO` | Enlaces que envía el bot |
| `SERVICE_API_KEY` | Clave de la API interna (`X-Service-Key`) |

### Cómo probarlo sin número de Meta

```bash
# Terminal 1
cd backend && NOTIFICADOR=log WHATSAPP_APP_SECRET=demo uvicorn app.main:app
# Terminal 2
cd backend && python -m app.seed
WHATSAPP_APP_SECRET=demo python ../scripts/simular_webhook.py 573000000001 "hola"
WHATSAPP_APP_SECRET=demo python ../scripts/simular_webhook.py 573000000001 "ORG-0042"
```

El script firma la carga como lo hace Meta, y las respuestas del bot aparecen en el log del backend. Las fotos solo se pueden probar con el número real, o en las pruebas automáticas.

### Robustez y privacidad

- **Webhook:** valida `hub.verify_token` y `X-Hub-Signature-256`, responde 200 enseguida y procesa con `BackgroundTasks`, sin colas externas.
- **Duplicados:** el id del mensaje de Meta se guarda con restricción `UNIQUE` en `mensajes_whatsapp.wa_message_id`, y los reintentos se descartan.
- **Ventana de 24 h:** dentro de ella se envía texto libre; fuera de ella, solo plantillas aprobadas.
- **Control de abuso:** `LIMITE_MENSAJES_DIA` por número, con un solo aviso al día. Hay tiempo máximo de espera en Claude (`IA_TIMEOUT_S`) y en la Graph API (`GRAPH_TIMEOUT_S`), con mensaje de contingencia al usuario.
- **Identidad:** el `wa_id` se normaliza a E.164 y se busca en `usuarios.telefono`. Un número no registrado solo recibe información general y el enlace de registro.
- **IA:** nunca recibe nombre, teléfono ni dirección. Solo recibe la descripción o la foto, re-codificada sin EXIF y reducida a 1024 px como máximo. Las fotos no se guardan.
- **`mensajes_whatsapp`:** guarda solo metadatos (`direccion`, `wa_id`, `tipo`, intención, estado de envío y `retener_hasta`), no el texto ni las fotos. Los registros vencidos se borran al arrancar, o con `POST /api/mantenimiento/purgar-mensajes`.
- **Consulta de estado:** si el código no existe o es de otra persona, la respuesta es la misma, para no revelar qué códigos existen. Del encargado solo se muestra el primer nombre.

### Limitaciones del número de prueba de Meta

- Solo puede escribir a un máximo de 5 números destinatarios, que hay que agregar y verificar en el panel.
- El token temporal vence a las 24 h.
- Las plantillas propias deben aprobarse antes de usarse. Mientras tanto, fuera de la ventana de 24 h solo funciona la plantilla `hello_world`.
- El nombre visible del número de prueba no se puede cambiar.

### Implementado, simulado y pendiente

- **Implementado:** todo lo de la tabla de arriba, la API interna mínima (`/api/solicitudes`, `/api/solicitudes/{codigo}/programar`, `/api/bandeja`, `/api/ia/sugerir`) y las pruebas automáticas.
- **Simulado:** en pruebas y demos locales, Meta y Claude se reemplazan por dobles (`ClienteFalso`, `NOTIFICADOR=log`).
- **Pendiente:** creación de la solicitud por chat (opcional), frontend web y autenticación de usuarios de la especificación principal, migraciones con Alembic (hoy se usa `create_all`) y retiro de `chatbot/`.

## Decisión de integración

El bot original (`chatbot/`) es Python, pero incumplía dos reglas del reto:

1. Usaba **Whapi.Cloud**, un intermediario no oficial de WhatsApp. Se reemplazó por la **WhatsApp Business Cloud API** de Meta.
2. Usaba **SQLite**. Se reemplazó por **PostgreSQL**.

Como es Python, se integró como **módulo del backend FastAPI** (`backend/app/whatsapp/`), con un solo webhook en `/webhook`. Se reutilizaron el vocabulario de reglas (`ia/reglas.py`) y el prompt de visión con Claude. El proveedor de IA (Claude API) no cambió. No había ninguna URL de webhook configurada en Meta (el bot apuntaba a Whapi), así que no hubo una URL que conservar.

### Supuestos (la especificación principal no está en el repositorio)

- Los códigos tienen el formato `ORG-0042` y `REC-0017`, con una secuencia por flujo.
- Los estados de una solicitud son `recibida`, `programada`, `completada` y `cancelada`.
- Los roles son `ciudadano`, `coordinador` (con `flujo`) y `recolector`. Las notificaciones de `nueva_solicitud` van a los coordinadores del flujo.
- La bandeja del coordinador es la tabla `casos_coordinacion`, con flujo `organico`, `reciclable` o `general`.
- El país por defecto para normalizar teléfonos es Colombia (`PAIS_TELEFONO=57`).

## Estructura

```
backend/
  app/
    main.py            FastAPI: /webhook, /api, /health
    config.py          variables de entorno
    db.py, models.py   PostgreSQL (usuarios, solicitudes, contenidos, mensajes_whatsapp, ...)
    solicitudes.py     reglas de negocio (las crean personas, nunca la IA)
    notificaciones.py  WhatsAppNotificador / LogNotificador (NOTIFICADOR)
    ia/                reglas -> modelo texto -> modelo visión; limpieza de fotos
    whatsapp/          webhook, firma, cliente Graph API, mensajería (24 h), bot, textos
    api/rutas.py       API interna (X-Service-Key)
    seed.py            datos de demostración
  tests/               pruebas (PostgreSQL real; Meta y Claude simulados)
scripts/simular_webhook.py
docs/                  arquitectura, demo, API legada
chatbot/               bot original (legado: Whapi + SQLite, no se despliega)
```

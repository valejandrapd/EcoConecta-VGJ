# EcoConecta Villas de San Pablo

Plataforma para conectar a hogares y unidades productivas de Villas de San Pablo (Barranquilla) con los **recicladores** de su zona, que recogen los residuos orgánicos (para la huerta comunitaria, donde apoyan los **voluntarios de huerta**) y los reciclables. Cubre la educación ambiental, la solicitud de recolección, la asignación, la programación, la recolección y los puntos. Es el reto oficial de la Hackathon Unilibre y la Fundación Santo Domingo (FSD), noviembre de 2026.

- **Frontend:** React con Next.js (`frontend/`), pensado para móvil y tableta. Sigue el Manual de Identidad Visual del reto: colores como tokens `--eco-*` en `app/globals.css`, Poppins para títulos e Inter para texto, y el logo original en `public/logo-ecoconecta.png`.
- **Backend:** Python, FastAPI, SQLAlchemy y Psycopg, con PostgreSQL (`backend/`).
- **Canal:** WhatsApp Business Cloud API de Meta (`backend/app/whatsapp/`).
- **IA:** Claude API con el SDK oficial de Anthropic. Hace una clasificación orientativa del residuo y no toma decisiones (`backend/app/ia/`).
- **URL publicada:** _pendiente del despliegue en la nube_.

## Tecnologías y cumplimiento (sección 8 del reto)

| Categoría | Permitido por el reto | Usado |
|---|---|---|
| Lenguajes | Python, TypeScript, JavaScript, HTML, CSS | Python |
| Base de datos | PostgreSQL | PostgreSQL 16 |
| Mensajería | WhatsApp Business Cloud API | WhatsApp Business Cloud API (Graph API), con `urllib` de la librería estándar |
| Modelos de IA | OpenAI, Azure OpenAI, Azure AI Foundry, Claude API | Claude API |
| Infraestructura | Docker y Git | Docker / Docker Compose, Git y GitHub |
| Backend Python | FastAPI, Flask, Django, SQLAlchemy, Psycopg, Pydantic, Pandas | FastAPI, SQLAlchemy, Psycopg, Pydantic |
| Agentes y modelos | SDK oficial de Anthropic, entre otros | SDK oficial de Anthropic (`anthropic`) |
| Frontend | React, Next.js, Vue | React 19 con Next.js 15 |
| Estilos | Tailwind CSS, Bootstrap | CSS propio (lenguaje permitido), sin librerías |

Dos librerías de apoyo no aparecen en la lista. Ninguna es una base de datos, un canal ni un proveedor de IA, y ninguna sustituye una herramienta autorizada:

- **`uvicorn`** es el servidor ASGI con el que se ejecuta FastAPI. Es el servidor que recomienda la propia documentación de FastAPI.
- **`Pillow`** quita los metadatos EXIF (por ejemplo, la ubicación GPS) y reduce las fotos a 1024 px antes de enviarlas a la IA. Cumple la sección 9: "no enviar información personal que no sea necesaria".

`pytest` y `httpx` solo se usan para las pruebas (`requirements-dev.txt`) y no van en la imagen de producción.

No se usan herramientas no-code ni low-code, ni otros servicios.

> **Atención: `chatbot/`.** Es el bot original del equipo y otro integrante lo está actualizando. Hoy usa Whapi.Cloud y SQLite, que el reto no permite (8.1). No se despliega ni forma parte de `docker-compose.yml`. Antes de la entrega debe migrarse a la WhatsApp Business Cloud API y a PostgreSQL, o integrarse en `backend/app/whatsapp/`.

## Arquitectura

```mermaid
flowchart LR
    U[Solicitante en WhatsApp] -- mensaje / foto --> META[WhatsApp Business Cloud API]
    META -- "POST /webhook (firma X-Hub-Signature-256)" --> WH
    WEB["frontend React/Next.js: usuario, coordinación de huerta y de reciclaje, admin"] -- "/api (Bearer token)" --> API
    subgraph backend [backend FastAPI]
        WH[whatsapp/webhook] -- BackgroundTasks --> BOT[whatsapp/bot]
        BOT --> IA[ia/cascada]
        BOT --> MSJ[whatsapp/mensajeria]
        API[api/rutas] --> SOL[solicitudes: RN-01 a RN-06] --> NOT[notificaciones] --> MSJ
        MSJ --> CLI[whatsapp/cliente]
    end
    IA -- texto o foto limpia --> CLAUDE[Claude API]
    CLI -- Graph API --> META
    backend --> PG[(PostgreSQL)]
```

Hay un solo webhook (`/webhook`) y un solo cliente de WhatsApp, que comparten el bot y las notificaciones. El detalle, con el modelo de datos, está en [`docs/arquitectura.md`](docs/arquitectura.md).

## Puesta en marcha local con Docker

```bash
cp .env.example .env          # completa los valores (nunca subas el .env)
docker compose up --build     # PostgreSQL + backend (:8000) + web (:3000)
docker compose exec -e DEMO_CLAVE=<clave> backend python -m app.seed   # datos FICTICIOS
```

- **Web:** `http://localhost:3000`.
- **API interactiva:** `http://localhost:8000/docs`.
- Las tablas se crean al arrancar el backend.

`app.seed` crea un usuario por perfil, todos ficticios y con la clave `DEMO_CLAVE` (si no la defines, se genera una y se imprime), y cuatro personas de campo sin cuenta: los recicladores Rosa (Sector 1, lun a vie, 7 a 12), Luis (Sector 2, lun, mié, vie y sáb, 8 a 17) y Marta (Sector 2, mar, jue y sáb, 13 a 18), y el voluntario de huerta Carlos, además de cuatro zonas ficticias (Sector 1 a Sector 4) que el administrador puede cambiar en la pestaña *Zonas*. En una base anterior, volver a correrlo agrega el personal y las zonas que falten.

| Perfil | Teléfono |
|---|---|
| Unidad productiva (Tienda La Esquina) | `DEMO_TELEFONO` o 3000000001 |
| Hogar | 3000000005 |
| Coordinación de huerta | 3000000003 |
| Coordinación de reciclaje | 3000000004 |
| Administración | 3000000007 |

Frontend sin Docker: `cd frontend && npm install && npm run dev`. El backend debe estar en `localhost:8000`, o indica otra dirección con `BACKEND_URL`.

### Pruebas

```bash
cd backend
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/ecoconecta_test python -m pytest
```

Son 46 pruebas contra PostgreSQL real. Simulan Meta y Claude, así que no necesitan credenciales. Incluyen el escenario mínimo de demostración de la sección 11 (`tests/test_flujo_reto.py`).

## Reglas del reto implementadas

| Regla | Cómo se cumple |
|---|---|
| **RN-01** Separación de flujos | Cada solicitud tiene `flujo`. La bandeja de cada coordinación solo muestra su flujo, y solo esa coordinación puede asignar, programar y cerrar |
| **RN-02** Programación | No se puede pasar a `programada` sin fecha, hora y reciclador (`reciclador_id`). La fecha y la hora deben caer en los días y horas que eligió el usuario **y** en el horario de servicio del reciclador |
| **RN-03** Asignación | `solicitudes.coordinador_id` y `solicitudes.reciclador_id`. Solo se ofrecen y aceptan recicladores activos de la zona de la solicitud cuyo horario cruza con el del usuario (`GET /solicitudes/{codigo}/opciones-asignacion`). Los voluntarios de huerta no recolectan |
| **RN-04** Trazabilidad | Código `ORG-0001` / `REC-0001`, estado y la tabla `historial_solicitudes`, que registra cada cambio con quién lo hizo |
| **RN-05** Cierre | Los puntos solo se crean en `recolecciones`, al registrar la recolección de una solicitud programada |
| **RN-06** Puntos | `puntos = PUNTOS_BASE_RECOLECCION + kg × PUNTOS_POR_KG_<FLUJO>`, redondeado hacia abajo. La fórmula aplicada queda guardada en `recolecciones.regla`. **Los valores son de ejemplo y no son reglas oficiales de FSD**: están sujetos a su validación. Cada solicitud indica a qué bonificación van sus puntos (`tiendas`: canje en tiendas de la zona; `huerto`: servicios del huerto). La alcancía sube un nivel cada 10 puntos de tiendas y la trinitaria crece cada 5 puntos del huerto, hasta el nivel 5 (florecida). Esto es una propuesta del equipo: falta definir con FSD qué se canjea con cada tipo de punto |
| **RN-07** Privacidad | El contacto y la dirección solo los ven el dueño, la coordinación del flujo y el administrador. El reciclador no usa la web: la coordinación le avisa por sus propios medios. Por WhatsApp, el estado solo se informa al número dueño y el reciclador se nombra solo por su nombre |
| **RN-08** Piloto | `usuarios.piloto` junto con `MODO_PILOTO=true`. Un usuario fuera del piloto solo recibe información general |

**Estados:** `recibida`, `en_revision`, `asignada`, `programada`, `recolectada` y `cancelada`.

**Perfiles con acceso:** solo cuatro: `solicitante` (el usuario; `tipo_generador`: hogar o unidad productiva), `coordinador_huerta`, `coordinador_reciclaje` y `administrador`. **Personal de campo sin cuenta** (`personal_campo`): recicladores (nombre, apellido, zona, días y horario de servicio) y voluntarios de huerta (nombre, apellido, días y horario). Los integra la coordinación. El reciclador marca la bolsa con el código (por ejemplo, ORG-0042) y la lleva a la huerta o al acopio, donde la coordinación registra los kg.

**Control humano (sección 9):** la asignación, la programación y el cierre se hacen solo desde la API con el perfil autorizado. La IA nunca llama a esas funciones.

### Web (`frontend/`)

| Perfil | Pantallas |
|---|---|
| Público | Inicio con contenidos educativos filtrables (separación, huerta, horarios y rutas), registro (con consentimiento de datos) e ingreso |
| Solicitante | Panel con dos insignias animadas (alcancía de tiendas y trinitaria del huerto), el botón **Crear solicitud** y sus solicitudes con estado, persona encargada, fecha y hora, historial, puntos y la opción de cancelar. **Crear solicitud** abre un asistente de un paso por pantalla (`/solicitudes/nueva`) con botones ilustrados: tipo de residuo (debajo, la ayuda por texto que responde "Tu residuo es ORGÁNICO / RECICLABLE" y el botón "Tómale una foto", aún sin función), consejos del material (reciclable: cartón seco, envases limpios y los códigos de plástico 1 a 7; orgánico: sin etiquetas), tamaño (botones uno debajo del otro (pequeño, mediano o grande, con dibujos según el tipo), días disponibles, franja horaria, confirmación de la dirección y su zona (o una nueva con zona y etiqueta, como "Casa mamá", que queda guardada), tipo de bonificación y resumen |
| Coordinación de huerta o de reciclaje | Botón **Integrar nuevo reciclador / voluntario de huerta** y pestaña con el personal (activar o desactivar). Bandeja de su flujo con pestañas (pendientes, asignadas, programadas, atendidas y canceladas): revisar, **asignar y programar en un paso** (solo recicladores de la zona, y solo los días y horas que cruzan con el usuario; avisa por WhatsApp), registrar la recolección (kg) y cancelar. Incluye los casos derivados por WhatsApp y un resumen por flujo, estado y periodo |
| Administración | Usuarios (perfil, piloto, activo, alta de personas), zonas (agregar, renombrar, desactivar), contenidos (crear, editar, borrar), todas las solicitudes y los parámetros de puntos |

El enlace que envía el bot (`/solicitudes/nueva?flujo=organico`) abre el formulario con el flujo ya elegido.

### API (`/api`)

- **Autenticación de la web:** `POST /auth/registro` y `POST /auth/login` devuelven un token, que luego se envía como `Authorization: Bearer <token>`. Las claves se guardan con scrypt y los tokens se firman con HMAC (`AUTH_SECRET`), todo con la librería estándar de Python.
- **Integraciones internas:** pueden usar `X-Service-Key` junto con `X-Usuario-Id`.
- **Rutas públicas:** `GET /contenidos`, `GET /parametros` y `GET /zonas` (zonas activas).

| Perfil | Rutas |
|---|---|
| Solicitante | `POST /solicitudes`, `GET /solicitudes/{codigo}`, `GET /solicitudes/{codigo}/historial`, `GET /mis-solicitudes` (incluye puntos e insignias), `GET /mis-direcciones`, `POST /solicitudes/{codigo}/cancelar` |
| Coordinador | `GET /bandeja?estado=` (solicitudes de su flujo y casos derivados por WhatsApp), `POST /solicitudes/{codigo}/revisar`, `GET /solicitudes/{codigo}/opciones-asignacion`, `POST /solicitudes/{codigo}/asignar` (con `fecha` y `hora` también programa), `/programar`, `/recoleccion`, `GET /resumen?desde=&hasta=` |
| Administrador | `GET/POST /usuarios`, `PATCH /usuarios/{id}` (perfil, piloto, activo), `GET /zonas/todas`, `POST /zonas`, `PATCH /zonas/{id}` (renombrar o desactivar), `POST/PUT/DELETE /contenidos`, `POST /mantenimiento/purgar-mensajes`, más todo lo anterior |
| Coordinación (personal de campo) | `GET /personal?tipo=`, `POST /personal`, `PATCH /personal/{id}` (activo) |
| Formulario web | `POST /ia/sugerir` (sugerencia orientativa, no crea nada) |

## Chatbot de WhatsApp

### Qué hace

| Función | Estado |
|---|---|
| Menú de bienvenida (`hola`, `menú`) con 7 opciones | Implementado |
| ¿Orgánico o reciclable? Por texto y por foto. Responde con sugerencia, confianza (alta, media o baja) y enlace al formulario. Si hay mezcla, sugiere dos solicitudes | Implementado. La IA solo sugiere |
| Consulta de estado por código (`ORG-0042`): estado, fecha, hora, persona encargada y puntos, solo para el número dueño | Implementado |
| Información educativa (separación, huerta, horarios, rutas), solo desde la tabla `contenidos` | Implementado. Los contenidos de `seed.py` son ejemplos que debe validar FSD |
| Mis puntos (`7`) | Implementado |
| Derivación a una persona (lo pide el usuario, o el bot no entiende dos veces seguidas). Se registra en la bandeja de la coordinación de huerta o de reciclaje | Implementado (`casos_coordinacion`) |
| Notificaciones `solicitud_recibida`, `nueva_solicitud` y `solicitud_programada` (día, hora y persona) | Implementado. Texto dentro de la ventana de 24 h, plantilla fuera de ella |
| Crear la solicitud completa por chat | Pendiente (opcional). El bot envía el enlace al formulario web |

### Configuración en Meta

1. En developers.facebook.com crea una app de tipo Business y agrega el producto **WhatsApp**.
2. Copia el *Phone number ID* y un token en `WHATSAPP_PHONE_NUMBER_ID` y `WHATSAPP_TOKEN`. El token temporal vence en 24 h; para la evaluación usa un token de usuario del sistema.
3. Copia la *clave secreta de la app* en `WHATSAPP_APP_SECRET`. Con ella se valida `X-Hub-Signature-256`.
4. Define un valor para `WHATSAPP_VERIFY_TOKEN`.
5. En *WhatsApp → Configuración → Webhook* pon la URL de callback `https://<URL publicada>/webhook` y el mismo verify token, y suscríbete al campo **messages**. En local puedes usar `ngrok http 8000`.
6. Crea y haz aprobar las plantillas `solicitud_recibida` ({{1}} = código), `nueva_solicitud` ({{1}} = código) y `solicitud_programada` ({{1}} = código, {{2}} = fecha, {{3}} = hora, {{4}} = persona encargada).
7. Pon `NOTIFICADOR=whatsapp`.

### Cómo probarlo sin número de Meta

```bash
cd backend
NOTIFICADOR=log WHATSAPP_APP_SECRET=demo uvicorn app.main:app      # terminal 1
python -m app.seed                                                 # terminal 2
WHATSAPP_APP_SECRET=demo python ../scripts/simular_webhook.py 573000000001 "ORG-0042"
```

El script firma la carga como lo hace Meta, y las respuestas aparecen en el log del backend (`LogNotificador`).

### Robustez y privacidad

- **Webhook:** valida `hub.verify_token` y `X-Hub-Signature-256`, responde 200 enseguida y procesa con `BackgroundTasks`, sin colas externas.
- **Duplicados:** el id del mensaje de Meta tiene restricción `UNIQUE` (`mensajes_whatsapp.wa_message_id`), y los reintentos se descartan.
- **Ventana de 24 h:** dentro de ella se envía texto libre; fuera de ella, solo plantillas aprobadas.
- **Control de abuso:** `LIMITE_MENSAJES_DIA` por número. Hay tiempo máximo de espera en Claude (`IA_TIMEOUT_S`) y en la Graph API (`GRAPH_TIMEOUT_S`), con mensaje de contingencia.
- **Identidad:** el `wa_id` se normaliza a E.164 y se busca en `usuarios.telefono`. Un número no registrado o fuera del piloto solo recibe información general.
- **IA (sección 9):** el modelo es el de `CLAUDE_MODEL` (por defecto `claude-sonnet-5-5`). Solo recibe la descripción del residuo o la foto, sin EXIF y de 1024 px como máximo; nunca nombre, teléfono ni dirección. El resultado es una sugerencia con nivel de confianza.
  - **Controles:** las reglas se aplican primero; la respuesta se valida contra categorías cerradas; si la IA falla o tarda, se envía un mensaje de contingencia; la respuesta aclara que es una sugerencia; y la persona siempre elige el flujo en el formulario.
  - Las fotos no se guardan.
- **`mensajes_whatsapp`:** guarda solo metadatos (`direccion`, `wa_id`, `tipo`, intención, estado de envío y `retener_hasta`). La retención se configura con `RETENCION_MENSAJES_DIAS`.

### Limitaciones del número de prueba de Meta

- Solo puede enviar mensajes a un máximo de 5 destinatarios verificados.
- El token temporal vence a las 24 h.
- Las plantillas propias requieren aprobación. Mientras tanto, fuera de la ventana de 24 h solo funciona `hello_world`.

## Variables de entorno

Todas están documentadas, sin valores, en [`.env.example`](.env.example):

- **Base de datos:** `DATABASE_URL`, `POSTGRES_PASSWORD`.
- **WhatsApp:** `NOTIFICADOR`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `GRAPH_API_VERSION`, `GRAPH_TIMEOUT_S`, `PLANTILLA_*`, `WHATSAPP_PLANTILLA_IDIOMA`.
- **IA:** `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `IA_MODELO_TEXTO`, `IA_MODELO_VISION`, `IA_TIMEOUT_S`.
- **Bot:** `LIMITE_MENSAJES_DIA`, `RETENCION_MENSAJES_DIAS`, `ZONA_HORARIA`, `PAIS_TELEFONO`, `URL_FORMULARIO_SOLICITUD`, `URL_REGISTRO`.
- **API y web:** `SERVICE_API_KEY`, `AUTH_SECRET`, `SESION_HORAS`.
- **Datos de demostración:** `DEMO_TELEFONO`, `DEMO_CLAVE`.
- **Frontend (al construir):** `BACKEND_URL`.
- **Reglas:** `MODO_PILOTO`, `PUNTOS_BASE_RECOLECCION`, `PUNTOS_POR_KG_ORGANICO`, `PUNTOS_POR_KG_RECICLABLE`.

## Infraestructura en la nube

_Pendiente._ Al desplegar hay que declarar aquí:

- el proveedor;
- el cómputo (los contenedores del backend y del frontend);
- la base de datos (PostgreSQL administrado);
- el almacenamiento (ninguno: las fotos no se guardan);
- las redes (HTTPS público para `/webhook`);
- la URL publicada.

## Implementado, simulado y pendiente

- **Implementado:** el modelo de datos y las reglas RN-01 a RN-08, la API por perfil, la autenticación, la web en React para los cinco perfiles, el bot de WhatsApp, las notificaciones, la IA orientativa y las pruebas del escenario mínimo (API y navegador).
- **Simulado:** en pruebas y demos locales, Meta y Claude se reemplazan por dobles (`NOTIFICADOR=log`, `ClienteFalso`). Todos los datos son ficticios.
- **Pendiente:**
  - despliegue en la nube con URL;
  - migración de `chatbot/` a la API oficial y PostgreSQL (la hace otro integrante);
  - recuperación de clave;
  - migraciones con Alembic (hoy se usa `create_all`);
  - creación de solicitudes por chat (opcional).

## Estructura

```
frontend/              React + Next.js: app/ (páginas), components/ (paneles por perfil), lib/api.js
backend/
  app/
    main.py            FastAPI: /webhook, /api, /health
    config.py          variables de entorno
    db.py, models.py   PostgreSQL: usuarios, solicitudes, historial_solicitudes, recolecciones,
                       contenidos, mensajes_whatsapp, conversaciones_whatsapp, casos_coordinacion
    solicitudes.py     reglas de negocio RN-01 a RN-06 (decisiones humanas)
    notificaciones.py  WhatsAppNotificador / LogNotificador (NOTIFICADOR)
    ia/                reglas -> modelo texto -> modelo visión; limpieza de fotos
    whatsapp/          webhook, firma, cliente Graph API, mensajería (24 h), bot, textos
    auth.py            claves (scrypt) y tokens firmados (HMAC)
    api/rutas.py       solicitudes, bandeja, asignaciones, resumen
    api/cuentas.py     registro, login, usuarios, contenidos, parámetros
    seed.py            datos ficticios de demostración
  tests/               pruebas (PostgreSQL real; Meta y Claude simulados)
scripts/simular_webhook.py
docs/                  arquitectura y guion de demo
chatbot/               bot original del equipo (en actualización; no se despliega)
```

# CLAUDE.md: guía para trabajar en EcoConecta

## Reglas del reto (no negociables)

- Canal: solo **WhatsApp Business Cloud API** oficial de Meta. Prohibidas las librerías de WhatsApp Web y los intermediarios no oficiales (Whapi, etc.).
- Base de datos: solo **PostgreSQL**.
- IA: OpenAI API, Azure OpenAI, Azure AI Foundry o **Claude API** (la que se usa hoy). Ningún otro proveedor.
- Prohibido no-code o low-code (n8n, Make, Zapier).
- La IA solo **sugiere**. Nunca crea, asigna, programa ni cierra solicitudes.

## Identidad visual

Toda pantalla sigue el Manual de Identidad Visual del reto: usa los tokens `--eco-*` de `frontend/app/globals.css` (no inventes tonos), Poppins para títulos e Inter para texto y botones, botón principal verde Eco con texto blanco, puntos y logros en amarillo, estados con texto e icono (no solo color), móvil primero. El logo es la imagen `public/logo-ecoconecta.png`: no se recrea con texto ni se recolorea, y se muestra con al menos 220 px de ancho sobre fondo claro. Las ilustraciones (`components/Ilustraciones.jsx`, `Insignias.jsx`) son planas, con un solo trazo verde bosque de 2 px.

## Estructura

- `frontend/`: React con Next.js (JS, CSS propio). `/api/*` se reenvía al backend (`next.config.mjs`). Hay un panel por perfil en `components/`.
- `frontend/app/solicitudes/nueva/page.jsx`: asistente de nueva solicitud (un paso por pantalla, botones ilustrados de `components/Opcion.jsx`).
- `backend/app/solicitudes.py`: reglas RN-01 a RN-06, tamaño/días/horario/bonificación de la solicitud e insignias. Todo cambio de estado pasa por `_cambiar_estado` (historial).
- `backend/app/api/`: `rutas.py` (operación) y `cuentas.py` (auth, usuarios, contenidos). Comprueba siempre el perfil del actor.
- `backend/app/whatsapp/`: el bot. Hay un solo webhook (`/webhook`) y un solo cliente (`cliente.py`) para el bot y las notificaciones. No dupliques código de envío: usa `mensajeria.enviar`, que aplica la ventana de 24 h y registra el envío.
- `backend/app/ia/`: cascada reglas, luego texto, luego visión. Fotos siempre por `imagen.preparar` (sin EXIF, máx. 1024 px).
- `backend/app/notificaciones.py`: `NOTIFICADOR=whatsapp|log`.
- `chatbot/`: bot original; otro integrante lo está actualizando. No lo modifiques sin coordinar. Hoy incumple el reto (Whapi + SQLite) y no se despliega.

## Privacidad

- A Claude nunca le envíes nombre, teléfono ni dirección.
- No guardes fotos ni el texto de los mensajes en `mensajes_whatsapp`: solo metadatos.
- RN-07: el estado de una solicitud solo se revela al número dueño. Si no existe o es ajena, el mensaje es el mismo.
- No escribas secretos en el código: todo va por variables de entorno (`.env.example` sin valores).

## Especificación

El PDF oficial del reto está en el material del proyecto (sección 5: alcance; 7: RN-01 a RN-08; 8: tecnologías permitidas). Ante dudas, manda el PDF.

## Base de datos

`crear_tablas()` crea las tablas y agrega las columnas opcionales nuevas a una base ya existente (`db._agregar_columnas_nuevas`). Una columna nueva debe ser opcional (`None` permitido) para que esa migración la agregue sola.

## Pruebas

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://u:p@localhost:5432/ecoconecta_test python -m pytest
```

Frontend: `cd frontend && npm run build`. Las pruebas usan PostgreSQL real y simulan Meta y Claude (`tests/conftest.py`: `ClienteFalso`, `publicar()` firma la carga).

## Convenciones

- Código y textos en español. Commits pequeños que no rompan el webhook.
- Trabaja en ramas y entra a `main` por pull request.

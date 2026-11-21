# Contrato entre el chatbot y el backend

El chatbot **no guarda la lógica de negocio**: pide todo al backend por esta API. Hoy usa un **backend provisional**
(`chatbot/core.py` + `chatbot/api.py`) para que la demostración funcione de punta a punta. Cuando el equipo tenga
el backend real, basta con que exponga estos endpoints y en `.env` se defina:

```
BACKEND_URL=https://TU-BACKEND/api/v1
BACKEND_API_KEY=...        # opcional; se envía en la cabecera X-API-Key
```

El bot no se modifica. La prueba `chatbot/test_contrato.py` verifica que el bot habla este contrato por HTTP.

## Lo que el bot necesita del backend (obligatorio)

| Endpoint | Para qué |
|---|---|
| `POST /solicitudes` | Crea la solicitud. Body: `contacto, canal, generador (hogar\|negocio), categoria (ORGANICO\|RECICLABLE), direccion, disponibilidad, observaciones?, objeto?, metodo?`. Devuelve la solicitud con `codigo` y `flujo` (`huerteros` para ORGANICO, `recicladores` para RECICLABLE). `400` si faltan datos |
| `GET /solicitudes/{codigo}?contacto=X` | Detalle. **Si `contacto` no es el dueño, responde `404`** (RN-07) |
| `GET /solicitudes?contacto=X&limite=3` | Últimas solicitudes de esa persona (más recientes primero) |
| `GET /puntos/{contacto}` | `{"puntos": N}`: suma de los puntos de sus solicitudes `recolectada` |

Campos de la solicitud que usa el bot: `codigo, flujo, estado, canal, contacto, recolector, puntos` y
`programacion: {dia, hora, recolector}` (null hasta que esté programada).
Estados: `recibida · en_revision · asignada · programada · recolectada · cancelada`.

## Avisos al usuario (el backend llama al bot)

Cuando el estado de una solicitud cambie (asignada, programada, recolectada, cancelada), el backend avisa al bot:

```
POST {URL_DEL_BOT}/api/v1/notificar      {"codigo": "RES-20261120-0001"}
```

El bot consulta la solicitud por `GET /solicitudes/{codigo}` y le escribe al usuario por WhatsApp el estado actual
(día, hora y persona encargada si está programada; puntos si fue recolectada). Solo notifica las de `canal = whatsapp`.

## Lo que hace el backend provisional y debe hacer el real (panel de coordinadores y recolectores)

| Endpoint provisional | Regla del reto |
|---|---|
| `POST /solicitudes/{codigo}/asignar` `{coordinador, recolector}` | RN-03 asociación coordinador–recolector |
| `POST /solicitudes/{codigo}/programar` `{dia, hora, recolector?}` | RN-02 no queda `programada` sin día, hora y persona |
| `POST /solicitudes/{codigo}/recolectar` `{cantidad_kg}` | RN-05 los puntos solo se dan al registrar la recolección (y solo si estaba programada) |
| `POST /solicitudes/{codigo}/cancelar` `{motivo}` | |
| `GET /solicitudes?flujo=&estado=` | Bandeja de cada coordinador |

Además el provisional guarda un **historial** de cada cambio de estado (RN-04) y calcula puntos con una regla
**parametrizable** (`PUNTOS_BASE`, `PUNTOS_POR_KG`); los valores por defecto son de demostración y **no son
oficiales** (RN-06: la Fundación debe validarlos).

## Lo que el bot hace y lo que NO

- El bot **sugiere** el tipo de residuo (palabras clave o foto con Claude) y **la persona lo confirma**.
- El bot **no asigna, no programa y no cierra** recolecciones: eso es humano (coordinador/recolector).
- A Claude solo se le envía la **foto** del residuo (nunca nombre, teléfono ni dirección).
- Contacto y dirección solo viajan al backend; el bot solo muestra a cada persona sus propias solicitudes.

## Pendiente del resto del equipo (fuera del chatbot)

Autenticación y perfiles (coordinador/recolector/administrador), panel de bandeja y programación, contenido
educativo publicado por el administrador (hoy `chatbot/contenido.py` es de ejemplo), modelo de datos y diagrama
de arquitectura, despliegue en la nube y la regla de puntos validada por la Fundación.

# API REST de EcoConecta (`/api/v1`)

Sirve al bot de WhatsApp, a una app o a una web. Es también el **contrato** que debe cumplir el backend real
(ver [`CONTRATO_BACKEND.md`](CONTRATO_BACKEND.md)). Todas las respuestas son JSON; los errores son `{"error": "mensaje"}`.

**Configuración opcional:** `API_KEY` (si se define, enviar cabecera `X-API-Key`), `CORS_ORIGINS` (orígenes web permitidos o `*`),
`MAX_FOTO_MB` (por defecto 8). Una clave puesta en el JavaScript de una web pública la puede ver cualquiera: desde webs públicas
llama a la API a través de tu backend.

## Identificar el residuo (no guarda nada)

`POST /clasificar` — JSON `{"texto": "cáscara de banano"}` o `multipart/form-data` con `foto` (JPG, PNG, WEBP o GIF).

```json
{"categoria": "ORGANICO", "metodo": "texto", "objeto": "", "necesita_foto": false, "foto_ilegible": false}
```
`categoria`: `ORGANICO | RECICLABLE | OTRO | null`. Si no se sabe, `necesita_foto: true`; si la foto no se ve, `foto_ilegible: true`.
Es una **sugerencia**: la persona debe confirmarla.

## Varios residuos a la vez (no guarda nada)

`POST /segmentar` — JSON `{"texto": "cáscaras de banano y hojas de papel"}` o `multipart/form-data` con `foto` (puede mostrar
varios residuos; en el celular un `<input type="file" accept="image/*" capture="environment">` abre la **cámara**) o `audio`
(`ogg`, `mp3`, `m4a`, `webm`, `wav`; se transcribe: requiere `STT_API_KEY`, si no responde `503`).

```json
{"metodo": "texto",
 "items": [{"objeto": "cáscaras de banano", "categoria": "ORGANICO"}, {"objeto": "hojas de papel", "categoria": "RECICLABLE"}],
 "grupos": {"ORGANICO": ["cáscaras de banano"], "RECICLABLE": ["hojas de papel"], "OTRO": [], "DUDA": []}}
```
Con `audio` incluye además `"transcripcion"`. `DUDA` = no se pudo decidir: pregúntale a la persona. `OTRO` = no aprovechable
(no genera solicitud). Es una **sugerencia**: confírmala con la persona y luego crea **una solicitud por cada tipo**
(`POST /solicitudes` con `categoria` y `objeto`) usando la misma dirección y disponibilidad. El contrato del backend no cambia.

## Solicitudes

`POST /solicitudes` — crea y enruta (RN-01). Campos mínimos: `contacto, generador (hogar|negocio), categoria (ORGANICO|RECICLABLE), direccion, disponibilidad`.
Opcionales: `observaciones, canal, objeto, metodo`. Devuelve `201` con la solicitud.

```json
{"codigo": "RES-20261120-0001", "contacto": "573001112233", "canal": "whatsapp", "generador": "negocio",
 "categoria": "ORGANICO", "flujo": "huerteros", "estado": "recibida", "direccion": "Calle 1 #2-3",
 "disponibilidad": "mañanas", "observaciones": "", "coordinador": null, "recolector": null,
 "dia": null, "hora": null, "programacion": null, "cantidad_kg": null, "puntos": 0,
 "creada": "2026-11-20T17:00:00+00:00", "actualizada": "2026-11-20T17:00:00+00:00",
 "historial": [{"estado": "recibida", "actor": "whatsapp", "detalle": "Solicitud registrada", "fecha": "..."}]}
```

`GET /solicitudes/{codigo}[?contacto=X]` — detalle e historial; con `contacto`, `404` si no es suya (RN-07).
`GET /solicitudes?contacto=&flujo=&estado=&limite=50` — listado (más recientes primero; sirve de bandeja por `flujo` y `estado`).
`GET /puntos/{contacto}` — `{"contacto": "...", "puntos": 20}`.

## Gestión (PROVISIONAL: lo hará el panel del backend real)

| Endpoint | Body | Regla |
|---|---|---|
| `POST /solicitudes/{codigo}/asignar` | `coordinador, recolector` | RN-03 |
| `POST /solicitudes/{codigo}/programar` | `dia, hora, recolector?` | RN-02: sin día, hora y persona no queda programada |
| `POST /solicitudes/{codigo}/recolectar` | `cantidad_kg` | RN-05/06: solo si estaba programada; calcula puntos |
| `POST /solicitudes/{codigo}/cancelar` | `motivo` | |
| `POST /notificar` | `codigo` | Avisa por WhatsApp el estado actual (lo usa el backend real) |

Estados: `recibida · en_revision · asignada · programada · recolectada · cancelada`. Un cambio no permitido responde `409`.

## Errores

`400` datos inválidos · `401` API key · `404` no existe (o no es tuya) · `409` transición no permitida · `413` foto muy grande ·
`502` falló la IA (reintenta).

## Ejemplos

```bash
curl -X POST http://localhost:5000/api/v1/solicitudes -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"contacto":"user-123","canal":"web","generador":"hogar","categoria":"RECICLABLE","direccion":"Calle 9 #8-7","disponibilidad":"tardes"}'

curl -X POST http://localhost:5000/api/v1/clasificar -H "X-API-Key: $API_KEY" -F foto=@residuo.jpg

curl -X POST http://localhost:5000/api/v1/segmentar -H "X-API-Key: $API_KEY" -F audio=@nota.ogg
```

```js
// Web / app: primero sugerir el tipo, la persona confirma, luego crear
const sug = await (await fetch(`${BASE}/api/v1/clasificar`, { method: "POST", body: formConFoto })).json();
const s = await (await fetch(`${BASE}/api/v1/solicitudes`, {
  method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": KEY },
  body: JSON.stringify({ contacto: usuario.id, canal: "web", generador: "hogar", categoria: sug.categoria,
                         direccion, disponibilidad }) })).json();
```

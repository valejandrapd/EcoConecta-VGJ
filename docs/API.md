# API REST de EcoConecta (`/api/v1`)

Sirve para conectar cualquier app (móvil) o web con el clasificador de residuos. Es el mismo núcleo
(`chatbot/core.py`) que usa el bot de WhatsApp, así que **las solicitudes de todos los canales viven en la
misma tabla** y se consultan con el mismo código `RES-AAAAMMDD-NNNN`.

## Configuración (variables de entorno, todas opcionales)

| Variable | Para qué |
|---|---|
| `API_KEY` | Si se define, cada petición debe traer `X-API-Key: <valor>`. **Actívala en producción.** |
| `CORS_ORIGINS` | Orígenes web permitidos, separados por coma (`https://miweb.com`) o `*`. |
| `MAX_FOTO_MB` | Tamaño máximo de la foto (por defecto 8). |
| `ANTHROPIC_API_KEY` | Necesaria para identificar por foto. |

> Si la API se llama desde una app móvil o desde un servidor, la `API_KEY` va en esa app/servidor.
> Una clave puesta en JavaScript de una web pública la puede ver cualquiera: para webs públicas, llama a la
> API desde tu backend o limita con `CORS_ORIGINS` y añade tu propia autenticación de usuarios.

## Respuesta (objeto solicitud)

```json
{
  "codigo": "RES-20261120-0001",
  "estado": "resuelta",            // "resuelta" | "esperando_foto"
  "categoria": "ORGANICO",         // ORGANICO | RECICLABLE | OTRO | null (si falta la foto)
  "metodo": "texto",               // "texto" | "foto" | null
  "objeto": "",                    // nombre del residuo si se identificó por foto
  "descripcion": "cáscara de banano",
  "contacto": "user-123",
  "canal": "api",
  "creada": "2026-11-20T17:00:00+00:00",
  "necesita_foto": false,          // true => la app debe pedir (o repetir) la foto
  "foto_ilegible": false           // true => la última foto no permitió distinguir el residuo
}
```

## Endpoints

### `POST /api/v1/solicitudes` — crear solicitud
- **JSON** `{"contacto": "user-123", "texto": "cáscara de banano", "canal": "web"}` → `201`.
  Si el texto no alcanza, `necesita_foto` viene en `true`.
- **multipart/form-data** con `contacto` y `foto` (y opcionalmente `texto`) → identifica por cámara en la misma petición.

`contacto` es quien pide: id de usuario de tu app, teléfono, correo… (texto libre). `canal` es opcional
(`api` por defecto; usa `web`, `app`, etc. para distinguir).

### `POST /api/v1/solicitudes/{codigo}/foto` — completar con la foto
multipart con el archivo `foto` (JPG, PNG, WEBP o GIF). Devuelve la solicitud resuelta (o `foto_ilegible: true`).

### `GET /api/v1/solicitudes/{codigo}` — consultar
### `GET /api/v1/solicitudes?contacto=user-123&limite=50` — listar (más recientes primero)

## Errores

`400` datos inválidos · `401` API key · `404` solicitud inexistente · `413` foto muy grande ·
`502` falló la IA (la solicitud sigue pendiente; reintenta). Cuerpo: `{"error": "mensaje"}`.

## Ejemplos

```bash
# Texto
curl -X POST http://localhost:5000/api/v1/solicitudes \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"contacto":"user-123","texto":"botella de plástico","canal":"web"}'

# Foto
curl -X POST http://localhost:5000/api/v1/solicitudes \
  -H "X-API-Key: $API_KEY" -F contacto=user-123 -F foto=@residuo.jpg
```

```js
// Web / app (fetch)
const r = await fetch(`${BASE}/api/v1/solicitudes`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": KEY },
  body: JSON.stringify({ contacto: usuario.id, texto, canal: "web" }),
});
let s = await r.json();
if (s.necesita_foto) {
  const f = new FormData(); f.append("foto", archivo);
  s = await (await fetch(`${BASE}/api/v1/solicitudes/${s.codigo}/foto`,
        { method: "POST", headers: { "X-API-Key": KEY }, body: f })).json();
}
```

## Usarlo sin HTTP (Python)

```python
import core, vision
r = core.registrar_texto("user-123", "cáscara de banano", canal="app")
if r["necesita_foto"]:
    r = core.adjuntar_foto("user-123", bytes_foto, "image/jpeg", vision.clasificar_foto, codigo=r["codigo"])
```

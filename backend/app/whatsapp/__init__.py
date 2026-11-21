"""Integración con WhatsApp Business Cloud API (oficial de Meta).

- `cliente`: único cliente HTTP de la Graph API (bot y notificaciones) + `ClienteLog` sin credenciales.
- `firma`: validación de X-Hub-Signature-256.
- `mensajeria`: envío con regla de ventana de 24 h y registro mínimo en `mensajes_whatsapp`.
- `bot`: lógica de conversación.
- `webhook`: rutas GET/POST /webhook.
"""

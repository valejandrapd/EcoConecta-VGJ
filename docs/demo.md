# Guion de demo

## Preparación

1. `docker compose up --build` con `NOTIFICADOR=whatsapp` y las credenciales del número de prueba de Meta.
2. `docker compose exec -e DEMO_TELEFONO=+57<tu número> backend python -m app.seed`. Esto registra tu número como "Ana Demo", con la solicitud `ORG-0042` programada para hoy a las 08:00 con Carlos.
3. Agrega tu número como destinatario de prueba en el panel de Meta.

## Interacción por WhatsApp (unos 3 minutos)

1. **Menú.** Escribe `hola`. El bot responde con el menú de 6 opciones.
2. **Foto de un residuo.** Escribe `3` y envía la foto de una botella. El bot responde algo como "Sugerencia (botella): *Reciclable* (confianza alta)", con el enlace al formulario `?flujo=reciclable`, y aclara que es una sugerencia.
3. **Mezcla.** Escribe `tengo cáscaras de papa y una lata`. El bot sugiere separar y hacer dos solicitudes, con un enlace para cada una.
4. **Consulta de estado.** Escribe `ORG-0042`. El bot responde estado *Programada*, la fecha de hoy, las 08:00 y el encargado Carlos.
5. **RN-07.** Desde otro número registrado, escribe `ORG-0042`. El bot responde "No encontré una solicitud con ese código asociada a este número" y no muestra ningún dato.
6. **Contenidos.** Escribe `horario`. El bot responde con los horarios cargados en la tabla `contenidos`.
7. **Derivación.** Escribe `quiero hablar con una persona`. El caso aparece en `GET /api/bandeja?flujo=organico`.
8. **Notificación.** Desde la web (o con `POST /api/solicitudes/ORG-0042/programar`), reprograma la solicitud. Llega el aviso `solicitud_programada`: es texto si escribiste en las últimas 24 h, y plantilla si no.

## Si no hay número de Meta

Usa `NOTIFICADOR=log` y `scripts/simular_webhook.py`, como se explica en el README. Las respuestas se ven en el log del backend.

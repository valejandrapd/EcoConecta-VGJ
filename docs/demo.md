# Guion de demo (escenario mínimo, sección 11 del reto)

## Preparación

1. `docker compose up --build`. Para enviar mensajes reales usa `NOTIFICADOR=whatsapp` y las credenciales del número de prueba de Meta.
2. `docker compose exec -e DEMO_TELEFONO=+57<tu número> -e DEMO_CLAVE=<clave> backend python -m app.seed`. Tu número queda como la unidad productiva "Tienda La Esquina", con la solicitud `ORG-0042` ya programada.
3. Agrega tu número como destinatario de prueba en Meta.
4. Abre `http://localhost:3000` (o la URL publicada) en un celular o una tableta.

## Recorrido web (unos 5 minutos)

1. **Información.** En el inicio, muestra los contenidos de separación, huerta, horarios y rutas.
2. **Solicitud orgánica.** Ingresa con tu número (la unidad productiva). En "Ayúdame", escribe `cáscaras de plátano`: la sugerencia es *orgánico*. Elige Orgánico, escribe la disponibilidad (`mañanas`) y envía. Aparece el código `ORG-00xx` con estado *Recibida*, y llega el aviso `solicitud_recibida` por WhatsApp.
3. **Enrutamiento y asignación.** Ingresa como coordinación de huerteros (3000000003). La solicitud está en *Pendientes*. Asígnala a "Carlos Huertero".
4. **Programación.** En *Asignadas*, elige fecha y hora y pulsa "Programar y avisar". Llega `solicitud_programada` con día, hora y persona.
5. **Recolección y puntos.** Ingresa como huertero (3000000002) y registra 4.5 kg. Vuelve como la unidad productiva: el estado es *Recolectada*, tienes 14 puntos y el historial muestra Recibida, Asignada, Programada y Recolectada.
6. **Separación de flujos.** Ingresa como hogar (3000000005) y crea una solicitud *Reciclable*. Ingresa como coordinación de recicladores (3000000004): la ves en su bandeja, y en la de huerteros no aparece.
7. **Panel.** Abre la pestaña *Resumen* (por flujo, estado y periodo). Como administración (3000000007), muestra los usuarios piloto, los contenidos y los parámetros de puntos.

## Interacción por WhatsApp (unos 2 minutos)

> El bot lo está actualizando otro integrante del equipo; ajusta estos pasos a su versión.

1. Escribe `hola` y aparece el menú.
2. Escribe `3` y envía la foto de una botella. La respuesta es una sugerencia *Reciclable* con su confianza y el enlace al formulario.
3. Escribe el código `ORG-0042`. La respuesta trae estado, fecha, hora y persona encargada.
4. Desde otro número, escribe el mismo código. El bot no revela nada (RN-07).

## Si no hay número de Meta

Usa `NOTIFICADOR=log` y `scripts/simular_webhook.py`. Los avisos aparecen en el log del backend.

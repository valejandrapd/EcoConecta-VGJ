# Guion de demo (escenario mínimo, sección 11 del reto)

## Preparación

1. `docker compose up --build`. Para enviar mensajes reales usa `NOTIFICADOR=whatsapp` y las credenciales del número de prueba de Meta.
2. `docker compose exec -e DEMO_TELEFONO=+57<tu número> -e DEMO_CLAVE=<clave> backend python -m app.seed`. Tu número queda como la unidad productiva "Tienda La Esquina", con la solicitud `ORG-0042` ya programada.
3. Agrega tu número como destinatario de prueba en Meta.
4. Abre `http://localhost:3000` (o la URL publicada) en un celular o una tableta.

## Recorrido web (unos 5 minutos)

1. **Información.** En el inicio, muestra los contenidos de separación, huerta, horarios y rutas.
2. **Solicitud orgánica.** Ingresa con tu número (la unidad productiva, Sector 1) y pulsa **Crear solicitud**. En "¿No sabes cuál es?", escribe `cáscaras de plátano`: aparece "Tu residuo es ORGÁNICO". Elige Orgánicos, lee el consejo (sin etiquetas), elige tamaño, lunes y jueves, la franja *Mañana*, confirma tu dirección y elige los puntos del huerto. Aparece el código `ORG-00xx` con estado *Recibida*, y llega el aviso `solicitud_recibida` por WhatsApp.
3. **Asignación por zona y horario.** Ingresa como coordinación de huerta (3000000003). La solicitud está en *Pendientes*. En "Asignar reciclador" solo aparece Rosa (Sector 1, mañanas). Luis y Marta no salen porque son de otra zona.
4. **Programación.** Elige uno de los días que se ofrecen (solo lunes o jueves) y una hora entre 7 y 12, y pulsa "Asignar y programar". Llega `solicitud_programada` con día, hora y el nombre del reciclador.
5. **Recolección y puntos.** En *Programadas*, registra 4.5 kg (el reciclador ya entregó en la huerta). Vuelve como la unidad productiva: el estado es *Recolectada*, tienes 14 puntos, la trinitaria creció y el historial muestra Recibida, Asignada, Programada y Recolectada.
6. **Separación de flujos.** Ingresa como hogar (3000000005) y crea una solicitud *Reciclable*: verás los consejos de cartón, envases y códigos de plástico. Ingresa como coordinación de reciclaje (3000000004): la ves en su bandeja, y en la de huerta no aparece. Con **Integrar nuevo reciclador / voluntario de huerta** agrega un reciclador del Sector 2 y comprueba que aparece como opción si su horario coincide.
7. **Panel.** Abre la pestaña *Resumen* (por flujo, estado y periodo). Como administración (3000000007), muestra los usuarios piloto, los contenidos y los parámetros de puntos.

## Interacción por WhatsApp (unos 2 minutos)

> El bot lo está actualizando otro integrante del equipo; ajusta estos pasos a su versión.

1. Escribe `hola` y aparece el menú.
2. Escribe `3` y envía la foto de una botella. La respuesta es una sugerencia *Reciclable* con su confianza y el enlace al formulario.
3. Escribe el código `ORG-0042`. La respuesta trae estado, fecha, hora y persona encargada.
4. Desde otro número, escribe el mismo código. El bot no revela nada (RN-07).

## Si no hay número de Meta

Usa `NOTIFICADOR=log` y `scripts/simular_webhook.py`. Los avisos aparecen en el log del backend.

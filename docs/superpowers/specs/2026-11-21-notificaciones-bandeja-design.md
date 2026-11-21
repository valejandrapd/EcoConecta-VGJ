# Bandeja de notificaciones del usuario (web)

Fecha: 2026-11-21 · Rama: `feat/notificaciones-web`

## Intención

El usuario solicitante no se entera de lo que pasa con su solicitud si no abre WhatsApp, y los vecinos
no saben cuándo pasa un reciclador por su zona. Queremos una **bandeja de entrada en la página web**
que le avise al usuario:

1. cuando su solicitud fue **asignada** a un reciclador;
2. la **fecha y hora** en que quedó **programada** la recogida;
3. que la recogida **está próxima** (recordatorio por fecha, no por distancia);
4. que un **reciclador pasará por su zona** en un día y hora, para animarlo a pedir una recolección
   si está libre: el aviso trae el botón **"Solicitar recolección"**.

"Estará en tu zona" se deduce de lo programado: si un reciclador tiene una recogida programada en la
zona Z el día D a la hora H, se asume que estará ahí ese día a esa hora. No hay GPS (los recicladores
son `personal_campo` sin cuenta ni app).

## Metas

- Bandeja web para el perfil `solicitante`, con contador de no leídas visible en la barra superior.
- Los cuatro tipos de aviso anteriores, sin duplicados.
- Marcar uno o todos como leídos.
- Botón "Solicitar recolección" en el aviso de zona.

## No metas

- Nada de GPS, tiempo estimado de llegada ni cuenta regresiva ("faltan 10 minutos").
- No se cambia el bot de WhatsApp ni sus notificaciones actuales (`notificaciones.py` sigue igual).
- No hay notificaciones push del navegador, correo ni tiempo real (websockets).
- Por ahora no hay bandeja para coordinadores ni administrador.
- No se agregan procesos en segundo plano, cron ni infraestructura nueva en Azure.

## Anti-metas (sería un fracaso aunque funcione)

- Que un aviso de zona revele **quién** recibe la visita (nombre, dirección o código de otra persona): RN-07.
- Que un usuario vea avisos de otro.
- Avisos repetidos: cinco recogidas del mismo reciclador en la misma zona y día deben dar **un** aviso
  de zona por vecino.
- Que la IA participe: los avisos salen solo de decisiones humanas (asignar y programar).

## Restricciones

- Reglas del reto (`CLAUDE.md`): solo PostgreSQL, FastAPI y Next.js; RN-07 (privacidad) y RN-08 (piloto).
- Tabla nueva creada con `crear_tablas()` (`Base.metadata.create_all`). Una tabla nueva no necesita
  `_agregar_columnas_nuevas`.
- Identidad visual: tokens `--eco-*`, botón principal verde Eco, estados con texto e icono (no solo
  color) y móvil primero.
- Hora local: `config().zona_horaria` (America/Bogota) para decidir "hoy" y "mañana".

## Enfoques considerados

1. **Generar los avisos por fecha al abrir la bandeja (elegido).** Los avisos "asignada" y "programada"
   se guardan en el momento de la acción. Los recordatorios y los avisos de zona se crean cuando el
   usuario pide su bandeja o su contador: el backend revisa qué falta y lo inserta, con una clave única
   que impide duplicados. No requiere procesos nuevos, y un vecino recién registrado también ve los
   avisos de zona vigentes. Desventaja: el recordatorio aparece al abrir la web, no a una hora exacta.
   En una bandeja web eso no importa.
2. **Proceso periódico dentro del backend.** Genera los avisos a la hora exacta para todos y serviría
   para enviarlos también por WhatsApp. Es más código, y hay que evitar que corra dos veces con varias
   réplicas. Descartado por ahora; se puede agregar después sin rehacer la bandeja.
3. **Tarea programada en Azure que llama a un endpoint.** Es lo más robusto, pero suma infraestructura
   sin efecto visible en la demo. Descartado.

El usuario eligió el enfoque 1.

## Diseño

### Modelo (`backend/app/models.py`)

Tabla `notificaciones`:

| columna | tipo | nota |
|---|---|---|
| id | int PK | |
| usuario_id | FK usuarios, index | destinatario |
| tipo | str(20) | `asignada` · `programada` · `recordatorio_manana` · `recordatorio_hoy` · `zona` |
| titulo | str(120) | |
| cuerpo | str(300) | texto ya armado en español |
| solicitud_id | FK solicitudes, null | solo en avisos de **su propia** solicitud; nunca en `zona` |
| accion | str(30), null | `nueva_solicitud` en avisos de zona |
| fecha_evento | date, null | día de la recogida o visita (para ordenar y ocultar vencidos) |
| clave | str(120), **unique** | evita duplicados (ver abajo) |
| leida_en | timestamptz, null | |
| creada_en | timestamptz | |

Claves:
- `asig:{solicitud_id}:{reciclador_id}`: un reasignar a otro reciclador genera un aviso nuevo.
- `prog:{solicitud_id}:{fecha}:{hora}`: reprogramar genera un aviso nuevo.
- `rec1:{solicitud_id}:{fecha}` y `rec0:{solicitud_id}:{fecha}`: mañana y hoy.
- `zona:{usuario_id}:{reciclador_id}:{zona}:{fecha}`.

Inserción con `INSERT … ON CONFLICT (clave) DO NOTHING`, como ya hace `mensajeria.registrar_entrante`.

### Lógica (`backend/app/bandeja.py`, módulo nuevo)

- `avisar_asignada(s, sol)`: lo llama `solicitudes.asignar` cuando el reciclador cambia (asignación
  nueva o reasignación). Texto: "Tu solicitud REC-0017 fue asignada a Juan Pérez. Pronto te diremos el
  día y la hora."
- `avisar_programada(s, sol)`: lo llama `solicitudes.programar`. Texto: "Juan Pérez pasará por tu
  solicitud REC-0017 el jueves 26/11 a las 9:00 a. m."
- `generar_pendientes(s, usuario)`: lo llaman los dos endpoints de lectura antes de responder.
  - **Recordatorios:** para cada solicitud del usuario en estado `programada` cuya `fecha_programada`
    sea mañana, se crea `recordatorio_manana` ("Mañana pasan por tu REC-0017 a las 9:00 a. m. Ten listos
    tus residuos."). Si la fecha es hoy, `recordatorio_hoy` ("Hoy pasan por tu REC-0017 a las…").
  - **Zona:** se calculan las zonas del usuario (`Usuario.zona` más las zonas de sus
    `DireccionUsuario`). Para cada combinación (reciclador, zona, fecha) con solicitudes `programada`
    entre hoy y los próximos 7 días, se crea un aviso `zona`: "Un reciclador pasará por {zona} el jueves
    26/11 desde las 9:00 a. m. ¿Tienes residuos? Pide tu recolección." Se usa la hora más temprana de
    ese día. Se omite si el usuario ya tiene una solicitud propia programada con ese reciclador ese día
    (ya recibió el aviso "programada").
  - **Avisos de la propia solicitud (respaldo):** si una solicitud del usuario está `asignada` o
    `programada` y no existe el aviso con la clave de su estado actual (`asig:` / `prog:`), se crea.
    Así las solicitudes que ya estaban asignadas o programadas antes de este cambio (incluidos los
    datos demo) también tienen sus avisos.
- **Avisos desactualizados de la propia solicitud:** al listar, un aviso `asignada`, `programada` o
  de recordatorio se oculta cuando ya no corresponde al estado actual de su solicitud. Eso pasa si la
  solicitud se canceló o se recolectó (los recordatorios), si cambió de reciclador, o si cambió de
  fecha u hora (el `programada` viejo y los recordatorios de la fecha vieja). Se compara la clave del
  aviso con el estado actual. La bandeja nunca debe mostrar una fecha equivocada.
- **Ocultar vencidos:** al listar, no se muestran los avisos `zona` ni los recordatorios con
  `fecha_evento` anterior a hoy. Tampoco los `zona` cuyo día ya no tenga ninguna solicitud `programada`
  de ese reciclador en esa zona (por ejemplo, si se canceló).
- **Retención:** se borran los avisos con más de 30 días, aprovechando el mismo llamado a
  `generar_pendientes` o la purga que ya existe en el arranque (`main.ciclo`).

### API (`backend/app/api/rutas.py` o un router nuevo incluido en `main.py`)

Solo para el perfil `solicitante`; los demás perfiles reciben una lista vacía y un contador en cero.

- `GET /api/notificaciones`: genera los pendientes y devuelve la lista, de la más nueva a la más
  vieja: `{id, tipo, titulo, cuerpo, codigo_solicitud?, accion?, fecha_evento?, leida, creada_en}`.
- `GET /api/notificaciones/contador`: genera los pendientes y devuelve `{no_leidas}`.
- `POST /api/notificaciones/{id}/leida`: responde 404 si el aviso no es del actor.
- `POST /api/notificaciones/leer-todas`.

### Web (`frontend/`)

- **Campana** en la barra superior (`app/layout.jsx`, junto a `<Menu />`). Solo aparece con sesión de
  solicitante. Muestra el número de no leídas en una burbuja; la etiqueta accesible dice "3
  notificaciones nuevas". Consulta el contador al cargar cada página.
- Entrada **"🔔 Notificaciones"** en el menú hamburguesa, con el mismo contador.
- **Página `/notificaciones`**: lista de tarjetas.

```
┌──────────────────────────────────────┐
│ 📍 Un reciclador pasará por tu zona  │  NUEVO
│ Villa Norte · jue 26/11 desde 9 a. m.│
│ ¿Tienes residuos? Pide tu recolección│
│ [ Solicitar recolección ]            │  ← botón verde Eco → /solicitudes/nueva
├──────────────────────────────────────┤
│ 📅 Recolección programada            │
│ Juan Pérez pasará por REC-0017 el    │
│ jueves 26/11 a las 9:00 a. m.        │
│ Ver mis solicitudes →                │  ← /panel
└──────────────────────────────────────┘
          [ Marcar todas como leídas ]
```

  Las no leídas llevan la etiqueta de texto "Nuevo" (no solo un color). Al abrir la página no se marcan
  como leídas automáticamente: se marcan al tocar la tarjeta o con "Marcar todas como leídas". Si no
  hay avisos: "No tienes notificaciones todavía."
- El botón "Solicitar recolección" solo aparece si el usuario es piloto (`yo.piloto`, RN-08). Si no lo
  es, el aviso se muestra igual, sin botón.

### Pruebas (`backend/tests/test_bandeja.py`)

- Asignar crea un aviso `asignada` para el dueño; reasignar a otro reciclador crea uno nuevo; reasignar
  al mismo no lo crea.
- Programar crea `programada` con fecha, hora y nombre; reprogramar crea otro.
- Con una solicitud programada para mañana u hoy, el listado incluye el recordatorio y no lo duplica en
  llamadas repetidas.
- Aviso de zona: un vecino de la misma zona lo recibe una sola vez aunque haya varias recogidas ese día.
  Un usuario de otra zona no lo recibe. El dueño de la solicitud no recibe el aviso de zona de su propia
  visita. El cuerpo no contiene nombre, dirección ni código de la solicitud ajena.
- Reprogramar oculta el `programada` viejo y el recordatorio de la fecha vieja; reasignar o cancelar
  oculta los avisos que ya no aplican. Una solicitud programada antes del cambio recibe sus avisos
  al abrir la bandeja.
- Un usuario no puede marcar como leído un aviso ajeno (404).
- Los perfiles distintos de solicitante reciben una lista vacía.
- Frontend: `npm run build` sin errores.

## Decisiones mías, para que las revises

- El aviso de zona no nombra al reciclador ("Un reciclador"), para minimizar datos.
- El aviso de zona llega a todos los solicitantes de la zona, pero el botón solo se muestra a los piloto.
- La ventana de avisos de zona es de 7 días hacia adelante y la retención de 30 días.
- La bandeja se marca como leída tocando cada aviso o con "Marcar todas", no al abrirla.
- No se agregó el aviso "asignada" por WhatsApp (la petición era solo para la web).
- Los avisos de la propia solicitud se ocultan cuando quedan desactualizados (reprogramación,
  reasignación, cancelación) en vez de marcarse como "reemplazado".
- Las solicitudes que ya estaban asignadas o programadas reciben sus avisos la primera vez que el
  usuario abre la bandeja (respaldo dentro de `generar_pendientes`, sin un paso de migración aparte).
- El aviso de zona sale de visitas de cualquier flujo (orgánico o reciclable), porque el reciclador
  recolecta ambos. El botón lleva al inicio del asistente (`/solicitudes/nueva`), sin flujo preelegido.
- El contador cuenta solo los avisos no leídos que están visibles.

## Queda a criterio de quien construya

- Si las rutas van en `rutas.py` o en un router nuevo.
- Iconos y textos finos de cada tipo, dentro del manual de identidad.
- Si la purga de avisos viejos va en `generar_pendientes` o en el arranque.

# Despliegue en Azure

EcoConecta corre en Azure con tres servicios administrados. No hace falta un servidor propio.

| Pieza | Servicio de Azure | Detalle |
|---|---|---|
| Web (Next.js) | Azure Container Apps (`ecoconecta-web`) | HTTPS público. Se apaga sin tráfico (`min-replicas 0`) |
| API y webhook de WhatsApp (FastAPI) | Azure Container Apps (`ecoconecta-api`) | HTTPS público. Encendida siempre (`MIN_REPLICAS=1`) para que el webhook responda rápido |
| Base de datos | Azure Database for PostgreSQL, servidor flexible (`ecoconecta-pg-<sufijo>`) | PostgreSQL 16, Burstable B1ms, 32 GB, conexión con TLS |
| IA | Azure OpenAI (`ecoconecta-ia-<sufijo>`, modelo `gpt-4.1-mini`) | Proveedor autorizado por el reto, pagado con el crédito de la suscripción |
| Imágenes | Azure Container Registry (`ecoconecta<sufijo>`) | Las imágenes se construyen en Azure (o con Docker local si la suscripción no lo permite) |

Las claves (base de datos, IA, WhatsApp, `AUTH_SECRET`) viajan como **secretos de Container Apps**. No quedan en el código ni en las imágenes.

## Lo que necesitas

1. Una suscripción de Azure. Con **Azure for Students** (US$100 de crédito, sin tarjeta) alcanza para el reto.
2. [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) y la sesión iniciada:
   ```bash
   az login
   ```
3. Python 3 y Git (ya los tiene el equipo). Docker solo si tu suscripción no permite construir en Azure.

## Desplegar

Desde la raíz del repositorio:

```bash
cp infra/azure/azure.env.example .env.azure   # .env.* no se sube a Git
# La IA (Azure OpenAI) la crea el script. Si ya tienen número de Meta, completa las variables WHATSAPP_*
bash infra/azure/desplegar.sh
```

La primera vez tarda entre 10 y 15 minutos (la base de datos es lo más lento). El script:

1. Genera y guarda en `.env.azure` lo que falte: sufijo de nombres, clave de PostgreSQL, `AUTH_SECRET`, `SERVICE_API_KEY` y la clave de los usuarios demo.
2. Crea el grupo de recursos, el registro, la base de datos y el entorno de Container Apps.
3. Construye y publica el backend, luego el frontend apuntando a la URL del backend.
4. Le pasa al bot los enlaces de la web (`URL_FORMULARIO_SOLICITUD`, `URL_REGISTRO`).
5. Comprueba `/health` y la portada, y muestra las URL.

Para **actualizar** después de nuevos cambios en la rama, vuelve a ejecutar el mismo comando. No borra datos.

## Datos de demostración

Con `SEMBRAR_DEMO=1`, al arrancar el backend carga zonas, recicladores y los usuarios demo si faltan. Los teléfonos son los de `docs/demo.md` y la clave es `DEMO_CLAVE` de `.env.azure` (no `demo1234`, porque la URL es pública). Para un piloto real, pon `SEMBRAR_DEMO=0` y crea las cuentas desde el panel del administrador.

## Conectar WhatsApp (Meta)

1. En `.env.azure` completa `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` (una cadena que tú inventas) y `WHATSAPP_NUMERO_PUBLICO`.
2. Ejecuta otra vez `bash infra/azure/desplegar.sh`. Con token y número, el bot pasa de modo log a enviar mensajes reales.
3. En Meta for Developers → tu app → WhatsApp → Configuración:
   - URL de devolución de llamada: `https://<API>/webhook` (el script la muestra al final).
   - Token de verificación: el mismo `WHATSAPP_VERIFY_TOKEN`.
   - Suscríbete al campo `messages`.

## Costo aproximado

Son cifras de referencia. Revisa la calculadora de Azure para tu región.

- PostgreSQL B1ms con 32 GB: unos US$15 al mes.
- Container Registry Basic: unos US$5 al mes.
- Azure OpenAI `gpt-4.1-mini`: centavos por cientos de consultas (se cobra por uso).
- Container Apps: la web casi siempre en cero; la API encendida, unos US$5 a 10 al mes. Hay una cuota gratuita mensual.

En total, entre US$20 y 30 al mes, que salen del crédito de Azure for Students. Para no gastar después del reto:

```bash
az group delete -n ecoconecta-rg      # borra TODO lo desplegado, incluida la base de datos
```

## Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| `RequestDisallowedByPolicy` o la región no está permitida | Azure for Students solo deja canadacentral, northcentralus, brazilsouth, chilecentral y francecentral. Cambia `AZ_REGION` en `.env.azure`, borra el grupo vacío si quedó creado (`az group delete -n ecoconecta-rg`) y vuelve a ejecutar |
| `TasksOperationsNotAllowed` al construir | El script cae solo a Docker local. Instala Docker y vuelve a ejecutar. Si `docker login` falla por un credential helper (`pass`), el script usa una configuración temporal de Docker |
| `SpecialFeatureOrQuotaIdRequired` con `gpt-4o-mini` | Esa suscripción no tiene cuota para ese modelo. Deja `AZ_REGION_IA=brazilsouth` y `AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini` (el script prueba también `gpt-4o-mini`). Sin IA, el bot usa las reglas por palabras |
| `RequestDisallowedByAzure` al crear Azure OpenAI | La política de Azure for Students no permite todas las regiones. Usa `AZ_REGION_IA=brazilsouth` (u otra permitida que tenga cuota: `canadacentral`, `northcentralus`, `francecentral`); la región de la web puede seguir siendo `canadacentral` |
| No pude crear Azure OpenAI | Solo se permite un recurso S0 por región. Cambia `AZ_REGION_IA` y vuelve a ejecutar |
| La web carga pero el login falla | `az containerapp logs show -g ecoconecta-rg -n ecoconecta-api --tail 50` |
| Meta no verifica el webhook | Revisa que el token coincida y que la API responda en `https://<API>/health` |

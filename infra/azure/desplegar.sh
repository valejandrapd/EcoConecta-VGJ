#!/usr/bin/env bash
# Despliega EcoConecta en Azure:
#   - Azure Container Registry: construye las imágenes en la nube (no necesitas Docker local)
#   - Azure Database for PostgreSQL (servidor flexible, Burstable B1ms)
#   - Azure Container Apps: backend (FastAPI, con el webhook de WhatsApp) y frontend (Next.js)
#
# Requisitos: Azure CLI (`az`) con sesión iniciada (`az login`) y el archivo .env.azure en la raíz.
# Azure for Students: gpt-4o-mini suele no tener cuota; se usa gpt-4.1-mini en brazilsouth como alternativa.
# Uso, desde la raíz del repo:   bash infra/azure/desplegar.sh
# Se puede volver a ejecutar: actualiza las imágenes y la configuración sin borrar datos.
# Los valores secretos nunca se imprimen.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
CONF="$RAIZ/.env.azure"
cd "$RAIZ"

paso() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
falla() { printf '\033[1;31mError: %s\033[0m\n' "$*" >&2; exit 1; }

command -v az >/dev/null || falla "No encuentro Azure CLI. Instálalo: https://learn.microsoft.com/cli/azure/install-azure-cli"
[ -f "$CONF" ] || { cp infra/azure/azure.env.example "$CONF"; echo "Creé .env.azure desde la plantilla. Revísalo y vuelve a ejecutar."; exit 1; }
az account show >/dev/null 2>&1 || falla "No hay sesión de Azure. Ejecuta: az login"

# Guarda una variable en .env.azure (sin mostrar su valor)
guardar() {
  local clave="$1" valor="$2"
  if grep -q "^${clave}=" "$CONF"; then
    python3 - "$CONF" "$clave" "$valor" <<'PY'
import sys
ruta, clave, valor = sys.argv[1:]
lineas = open(ruta).read().splitlines()
open(ruta, "w").write("\n".join(f"{clave}={valor}" if l.startswith(clave + "=") else l for l in lineas) + "\n")
PY
  else
    printf '%s=%s\n' "$clave" "$valor" >> "$CONF"
  fi
}
aleatorio() { python3 -c "import secrets; print(secrets.token_hex($1))"; }

set -a; . "$CONF"; set +a

REGION_IA="${AZ_REGION_IA:-brazilsouth}"
API_VERSION_IA="${AZURE_OPENAI_API_VERSION:-2025-04-01-preview}"

# Valores generados una sola vez
if [ -z "${AZ_SUFIJO:-}" ]; then AZ_SUFIJO="$(az account show --query id -o tsv | sha1sum | cut -c1-6)"; guardar AZ_SUFIJO "$AZ_SUFIJO"; fi
if [ -z "${PG_CLAVE:-}" ]; then PG_CLAVE="Eco$(aleatorio 12)9"; guardar PG_CLAVE "$PG_CLAVE"; fi
if [ -z "${AUTH_SECRET:-}" ]; then AUTH_SECRET="$(aleatorio 32)"; guardar AUTH_SECRET "$AUTH_SECRET"; fi
if [ -z "${SERVICE_API_KEY:-}" ]; then SERVICE_API_KEY="$(aleatorio 24)"; guardar SERVICE_API_KEY "$SERVICE_API_KEY"; fi
if [ "${SEMBRAR_DEMO:-0}" = "1" ] && [ -z "${DEMO_CLAVE:-}" ]; then DEMO_CLAVE="$(aleatorio 6)"; guardar DEMO_CLAVE "$DEMO_CLAVE"; fi

GRUPO="${AZ_GRUPO:-ecoconecta-rg}"
REGION="${AZ_REGION:-canadacentral}"
ACR="ecoconecta${AZ_SUFIJO}"
PG="ecoconecta-pg-${AZ_SUFIJO}"
ENTORNO="ecoconecta-env"
BACK="ecoconecta-api"
FRONT="ecoconecta-web"
ETIQUETA="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)"

paso "Suscripción: $(az account show --query name -o tsv) · grupo $GRUPO · región $REGION"
az extension add --name containerapp --upgrade --only-show-errors >/dev/null
for proveedor in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry Microsoft.DBforPostgreSQL Microsoft.CognitiveServices; do
  az provider register --namespace "$proveedor" --only-show-errors >/dev/null
done
az group create -n "$GRUPO" -l "$REGION" --only-show-errors -o none

paso "Registro de contenedores ($ACR)"
if ! az acr show -n "$ACR" -o none 2>/dev/null; then
  az acr create -g "$GRUPO" -n "$ACR" --sku Basic --admin-enabled true -l "$REGION" --only-show-errors -o none
fi
ACR_SERVIDOR="$(az acr show -n "$ACR" --query loginServer -o tsv)"
ACR_USUARIO="$(az acr credential show -n "$ACR" --query username -o tsv)"
ACR_CLAVE="$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)"

paso "PostgreSQL ($PG). La primera vez tarda unos 5 minutos"
if ! az postgres flexible-server show -g "$GRUPO" -n "$PG" -o none 2>/dev/null; then
  az postgres flexible-server create -g "$GRUPO" -n "$PG" -l "$REGION" \
    --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 \
    --admin-user "$PG_ADMIN" --admin-password "$PG_CLAVE" \
    --public-access 0.0.0.0 --yes --only-show-errors -o none
fi
az postgres flexible-server db show -g "$GRUPO" -s "$PG" -d ecoconecta -o none 2>/dev/null \
  || az postgres flexible-server db create -g "$GRUPO" -s "$PG" -d ecoconecta --only-show-errors -o none
PG_HOST="$(az postgres flexible-server show -g "$GRUPO" -n "$PG" --query fullyQualifiedDomainName -o tsv)"
DATABASE_URL="postgresql+psycopg://${PG_ADMIN}:${PG_CLAVE}@${PG_HOST}:5432/ecoconecta?sslmode=require"

AOAI="${AZURE_OPENAI_RECURSO:-ecoconecta-ia-${AZ_SUFIJO}}"
if [ "${IA_PROVEEDOR:-}" = "azure_openai" ] && [ "${CREAR_AZURE_OPENAI:-0}" = "1" ] && [ -z "${AZURE_OPENAI_API_KEY:-}" ]; then
  paso "Azure OpenAI ($AOAI, región $REGION_IA)"

  # Si el recurso ya existe en otra región, creamos uno nuevo con la región en el nombre.
  AOAI_EN_AZ="0"
  if az cognitiveservices account show -g "$GRUPO" -n "$AOAI" -o none 2>/dev/null; then
    AOAI_EN_AZ="1"
    REGION_ACTUAL="$(az cognitiveservices account show -g "$GRUPO" -n "$AOAI" --query location -o tsv | tr -d '[:space:]')"
    if [ "$REGION_ACTUAL" != "$REGION_IA" ]; then
      AOAI="${AOAI}-${REGION_IA}"
      AOAI_EN_AZ="0"
    fi
  fi

  if [ "$AOAI_EN_AZ" = "0" ]; then
    az cognitiveservices account create -g "$GRUPO" -n "$AOAI" -l "$REGION_IA" \
      --kind OpenAI --sku S0 --custom-domain "$AOAI" --yes --only-show-errors -o none \
      || echo "No pude crear Azure OpenAI en $REGION_IA. Sigo sin IA (las reglas por palabras funcionan)."
  fi

  if az cognitiveservices account show -g "$GRUPO" -n "$AOAI" -o none 2>/dev/null; then
    DEPLOY_IA="${AZURE_OPENAI_DEPLOYMENT:-gpt-4.1-mini}"
    if ! az cognitiveservices account deployment show -g "$GRUPO" -n "$AOAI" --deployment-name "$DEPLOY_IA" -o none 2>/dev/null; then
      if [ -n "${AZURE_OPENAI_MODELO:-}" ]; then
        CANDIDATOS_IA=("${AZURE_OPENAI_MODELO}|${AZURE_OPENAI_MODELO_VERSION:-}")
      else
        # gpt-4o-mini no tiene cuota en Azure for Students; gpt-4.1-mini sí suele tenerla en brazilsouth.
        CANDIDATOS_IA=("gpt-4.1-mini|2025-04-14" "gpt-4o-mini|2024-07-18")
      fi
      MODELO_IA=""
      for CANDIDATO_IA in "${CANDIDATOS_IA[@]}"; do
        MODELO_IA="${CANDIDATO_IA%%|*}"
        VERSION_IA="${CANDIDATO_IA#*|}"
        if az cognitiveservices account deployment create -g "$GRUPO" -n "$AOAI" \
             --deployment-name "$DEPLOY_IA" --model-name "$MODELO_IA" --model-version "$VERSION_IA" \
             --model-format OpenAI --sku-name GlobalStandard --sku-capacity 10 --only-show-errors -o none; then
          guardar AZURE_OPENAI_MODELO "$MODELO_IA"
          guardar AZURE_OPENAI_MODELO_VERSION "$VERSION_IA"
          guardar AZURE_OPENAI_DEPLOYMENT "$DEPLOY_IA"
          break
        fi
      done
      if ! az cognitiveservices account deployment show -g "$GRUPO" -n "$AOAI" --deployment-name "$DEPLOY_IA" -o none 2>/dev/null; then
        echo "No pude desplegar el modelo. Revisa la cuota en Azure AI Foundry; sigo sin IA."
      fi
    fi
    AZURE_OPENAI_ENDPOINT="$(az cognitiveservices account show -g "$GRUPO" -n "$AOAI" --query properties.endpoint -o tsv)"
    AZURE_OPENAI_API_KEY="$(az cognitiveservices account keys list -g "$GRUPO" -n "$AOAI" --query key1 -o tsv)"
  fi
fi

paso "Entorno de Container Apps"
if ! az containerapp env show -g "$GRUPO" -n "$ENTORNO" -o none 2>/dev/null; then
  az containerapp env create -g "$GRUPO" -n "$ENTORNO" -l "$REGION" --only-show-errors -o none
fi

# Construye en Azure (ACR Tasks). Algunas suscripciones (prueba gratuita, estudiantes) no permiten
# ACR Tasks: en ese caso se construye con Docker local y se sube la imagen.
construir() {  # imagen carpeta [build-arg]
  local imagen="$1" carpeta="$2" arg="${3:-}"
  if az acr build -r "$ACR" -t "$imagen" ${arg:+--build-arg "$arg"} "$carpeta" --only-show-errors -o none; then
    return 0
  fi
  echo "ACR Tasks no está disponible; construyo con Docker local."
  command -v docker >/dev/null || falla "Necesito Docker instalado para construir la imagen localmente."

  # Un credential helper (p. ej. pass) sin inicializar puede romper 'docker login'.
  # Usamos una configuración temporal solo durante el despliegue.
  if [ -z "${DOCKER_CONFIG_TEMP:-}" ]; then
    DOCKER_CONFIG_TEMP="$(mktemp -d)"
    ORIGEN_DOCKER="${DOCKER_CONFIG:-$HOME/.docker}"
    [ ! -f "$ORIGEN_DOCKER/config.json" ] || cp "$ORIGEN_DOCKER/config.json" "$DOCKER_CONFIG_TEMP/config.json"
    [ ! -d "$ORIGEN_DOCKER/contexts" ] || cp -R "$ORIGEN_DOCKER/contexts" "$DOCKER_CONFIG_TEMP/"
    python3 - "$DOCKER_CONFIG_TEMP/config.json" <<'PY'
import json, os, sys
ruta = sys.argv[1]
datos = json.load(open(ruta)) if os.path.exists(ruta) else {}
datos.pop("credsStore", None)
datos.pop("credHelpers", None)
json.dump(datos, open(ruta, "w"))
PY
    trap '[ -z "${DOCKER_CONFIG_TEMP:-}" ] || rm -rf "$DOCKER_CONFIG_TEMP"' EXIT
  fi
  export DOCKER_CONFIG="$DOCKER_CONFIG_TEMP"
  printf '%s' "$ACR_CLAVE" | docker login "$ACR_SERVIDOR" -u "$ACR_USUARIO" --password-stdin >/dev/null \
    || falla "No pude iniciar sesión en $ACR_SERVIDOR con Docker."

  docker build -t "$ACR_SERVIDOR/$imagen" ${arg:+--build-arg "$arg"} "$carpeta"
  docker push "$ACR_SERVIDOR/$imagen"
}

paso "Imagen del backend"
construir "backend:$ETIQUETA" ./backend

# Secretos: solo los que tienen valor. Nunca se imprimen.
SECRETOS=("database-url=$DATABASE_URL" "auth-secret=$AUTH_SECRET" "service-api-key=$SERVICE_API_KEY")
ENV_BACK=("DATABASE_URL=secretref:database-url" "AUTH_SECRET=secretref:auth-secret" "SERVICE_API_KEY=secretref:service-api-key"
          "MODO_PILOTO=${MODO_PILOTO:-true}" "SEMBRAR_DEMO=${SEMBRAR_DEMO:-0}")
[ -z "${WHATSAPP_NUMERO_PUBLICO:-}" ] || ENV_BACK+=("WHATSAPP_NUMERO_PUBLICO=$WHATSAPP_NUMERO_PUBLICO")
[ -z "${WHATSAPP_PHONE_NUMBER_ID:-}" ] || ENV_BACK+=("WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID")
agregar_secreto() {  # nombre-secreto VARIABLE valor
  [ -n "$3" ] || return 0
  SECRETOS+=("$1=$3"); ENV_BACK+=("$2=secretref:$1")
}
agregar_secreto demo-clave DEMO_CLAVE "${DEMO_CLAVE:-}"
agregar_secreto anthropic-api-key ANTHROPIC_API_KEY "${ANTHROPIC_API_KEY:-}"
agregar_secreto azure-openai-key AZURE_OPENAI_API_KEY "${AZURE_OPENAI_API_KEY:-}"
[ -z "${IA_PROVEEDOR:-}" ] || ENV_BACK+=("IA_PROVEEDOR=$IA_PROVEEDOR")
[ -z "${AZURE_OPENAI_ENDPOINT:-}" ] || ENV_BACK+=("AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" "AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT:-gpt-4.1-mini}" "AZURE_OPENAI_API_VERSION=$API_VERSION_IA")
agregar_secreto whatsapp-token WHATSAPP_TOKEN "${WHATSAPP_TOKEN:-}"
agregar_secreto whatsapp-verify-token WHATSAPP_VERIFY_TOKEN "${WHATSAPP_VERIFY_TOKEN:-}"
agregar_secreto whatsapp-app-secret WHATSAPP_APP_SECRET "${WHATSAPP_APP_SECRET:-}"
[ -z "${CLAUDE_MODEL:-}" ] || ENV_BACK+=("CLAUDE_MODEL=$CLAUDE_MODEL")
if [ -n "${WHATSAPP_TOKEN:-}" ] && [ -n "${WHATSAPP_PHONE_NUMBER_ID:-}" ]; then ENV_BACK+=("NOTIFICADOR=whatsapp"); else ENV_BACK+=("NOTIFICADOR=log"); fi

paso "Backend ($BACK)"
if az containerapp show -g "$GRUPO" -n "$BACK" -o none 2>/dev/null; then
  az containerapp secret set -g "$GRUPO" -n "$BACK" --secrets "${SECRETOS[@]}" --only-show-errors -o none
  az containerapp update -g "$GRUPO" -n "$BACK" --image "$ACR_SERVIDOR/backend:$ETIQUETA" \
    --min-replicas "${MIN_REPLICAS:-1}" --max-replicas 2 --set-env-vars "${ENV_BACK[@]}" --only-show-errors -o none
else
  az containerapp create -g "$GRUPO" -n "$BACK" --environment "$ENTORNO" \
    --image "$ACR_SERVIDOR/backend:$ETIQUETA" --target-port 8000 --ingress external \
    --registry-server "$ACR_SERVIDOR" --registry-username "$ACR_USUARIO" --registry-password "$ACR_CLAVE" \
    --cpu 0.5 --memory 1.0Gi --min-replicas "${MIN_REPLICAS:-1}" --max-replicas 2 \
    --secrets "${SECRETOS[@]}" --env-vars "${ENV_BACK[@]}" --only-show-errors -o none
fi
BACK_URL="https://$(az containerapp show -g "$GRUPO" -n "$BACK" --query properties.configuration.ingress.fqdn -o tsv)"

paso "Imagen del frontend (apunta a $BACK_URL)"
construir "frontend:$ETIQUETA" ./frontend "BACKEND_URL=$BACK_URL"

paso "Frontend ($FRONT)"
if az containerapp show -g "$GRUPO" -n "$FRONT" -o none 2>/dev/null; then
  az containerapp update -g "$GRUPO" -n "$FRONT" --image "$ACR_SERVIDOR/frontend:$ETIQUETA" --only-show-errors -o none
else
  az containerapp create -g "$GRUPO" -n "$FRONT" --environment "$ENTORNO" \
    --image "$ACR_SERVIDOR/frontend:$ETIQUETA" --target-port 3000 --ingress external \
    --registry-server "$ACR_SERVIDOR" --registry-username "$ACR_USUARIO" --registry-password "$ACR_CLAVE" \
    --cpu 0.5 --memory 1.0Gi --min-replicas 0 --max-replicas 2 --only-show-errors -o none
fi
WEB_URL="https://$(az containerapp show -g "$GRUPO" -n "$FRONT" --query properties.configuration.ingress.fqdn -o tsv)"

paso "Enlaces del bot hacia la web"
az containerapp update -g "$GRUPO" -n "$BACK" --only-show-errors -o none --set-env-vars \
  "URL_FORMULARIO_SOLICITUD=$WEB_URL/solicitudes/nueva" "URL_REGISTRO=$WEB_URL/registro"

paso "Comprobación"
for i in $(seq 1 30); do
  if curl -fsS "$BACK_URL/health" >/dev/null 2>&1; then break; fi
  sleep 10
done
curl -fsS "$BACK_URL/health" >/dev/null && echo "Backend OK" || echo "El backend aún no responde; revisa: az containerapp logs show -g $GRUPO -n $BACK --tail 50"
curl -fsS -o /dev/null "$WEB_URL/" && echo "Web OK" || echo "La web aún no responde; revisa: az containerapp logs show -g $GRUPO -n $FRONT --tail 50"

cat <<FIN

Listo.
  Web:               $WEB_URL
  API:               $BACK_URL
  Webhook de Meta:   $BACK_URL/webhook   (token de verificación = WHATSAPP_VERIFY_TOKEN de .env.azure)
  Usuarios demo:     la clave está en .env.azure (DEMO_CLAVE)
FIN

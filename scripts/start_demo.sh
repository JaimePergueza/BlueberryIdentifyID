#!/usr/bin/env sh
set -eu

ENV_FILE="${1:-.env.docker}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file '$ENV_FILE' does not exist. Copy .env.docker.example and replace CHANGE_ME values." >&2
  exit 1
fi

echo "Building and starting BlueberryMicroID..."
docker compose --env-file "$ENV_FILE" up -d --build postgres redis migrate api worker frontend

APP_PORT_VALUE=$(awk -F= '/^APP_PORT=/{print $2; exit}' "$ENV_FILE")
APP_PORT_VALUE=${APP_PORT_VALUE:-8080}
HEALTH_URL="http://127.0.0.1:${APP_PORT_VALUE}/health"

echo "Waiting for $HEALTH_URL ..."
healthy=0
attempt=1
while [ "$attempt" -le 60 ]; do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done

if [ "$healthy" -ne 1 ]; then
  docker compose --env-file "$ENV_FILE" logs --tail=200
  echo "The public application did not become healthy." >&2
  exit 1
fi

echo "Creating idempotent synthetic demonstration data..."
docker compose --env-file "$ENV_FILE" --profile demo run --rm demo-seed

echo "Running full-stack smoke test..."
docker compose --env-file "$ENV_FILE" --profile demo run --rm demo-smoke

echo
echo "BlueberryMicroID is ready at http://127.0.0.1:${APP_PORT_VALUE}"
echo "Use the demo credentials configured in $ENV_FILE."

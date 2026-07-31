# Despliegue reproducible y demostración del MVP

Esta guía levanta BlueberryMicroID como un sistema completo mediante Docker
Compose. La única entrada pública es Nginx; PostgreSQL, Redis, FastAPI y Celery
permanecen en la red interna de Compose.

## Servicios

| Servicio | Función |
| --- | --- |
| `postgres` | Persistencia relacional. |
| `redis` | Broker y resultados de Celery. |
| `migrate` | Ejecuta `alembic upgrade head` una vez antes de iniciar la API. |
| `api` | FastAPI autenticado. |
| `worker` | Worker Celery para el recorrido asíncrono legado/técnico. |
| `frontend` | SPA React compilada y servida por Nginx; proxy de `/api` y `/health`. |
| `demo-seed` | Crea usuarios y tres casos sintéticos idempotentes. Perfil `demo`. |
| `demo-smoke` | Valida el recorrido desplegado desde el origen público. Perfil `demo`. |

Los volúmenes persistentes son:

- `blueberry_postgres_data`;
- `blueberry_redis_data`;
- `blueberry_storage`.

## Requisitos

- Docker Desktop o Docker Engine con Compose v2.
- Al menos 4 GB de memoria disponible para Docker.
- Puerto `8080` libre, o cambiar `APP_PORT`.
- No es necesario instalar Python, Node, PostgreSQL ni Redis en la máquina de demostración.

## Preparación

1. Copiar la plantilla:

```powershell
Copy-Item .env.docker.example .env.docker
```

2. Abrir `.env.docker` y reemplazar todos los valores `CHANGE_ME`.

Las contraseñas de demostración deben tener al menos 12 caracteres. El archivo
`.env.docker` está ignorado por Git y nunca debe compartirse ni subirse al
repositorio.

## Inicio recomendado en Windows

```powershell
./scripts/start_demo.ps1
```

El script:

1. construye las imágenes;
2. inicia PostgreSQL y Redis;
3. aplica migraciones;
4. inicia API, worker y frontend;
5. espera el health check público;
6. crea datos sintéticos de demostración;
7. ejecuta el smoke test completo.

Al finalizar, abre:

```text
http://127.0.0.1:8080
```

Usa el usuario especialista configurado en `DEMO_SPECIALIST_USERNAME` para el
recorrido cotidiano. Conserva el usuario administrador para la gestión de
cuentas y rutas técnicas.

## Inicio en Linux/macOS

```bash
chmod +x scripts/start_demo.sh
./scripts/start_demo.sh
```

## Comandos manuales equivalentes

```bash
docker compose --env-file .env.docker up -d --build postgres redis migrate api worker frontend
docker compose --env-file .env.docker --profile demo run --rm demo-seed
docker compose --env-file .env.docker --profile demo run --rm demo-smoke
```

## Datos de demostración

El seed crea imágenes sintéticas mediante Pillow; no incorpora muestras reales
ni información personal. Los códigos son:

| Código | Estado preparado |
| --- | --- |
| `DEMO-BB-001` | Revisión confirmada. |
| `DEMO-BB-002` | Revisión corregida a no concluyente. |
| `DEMO-BB-003` | Pendiente de revisión. |

El seed es idempotente: volver a ejecutarlo no duplica esos análisis. También
crea o actualiza el administrador y especialista configurados y revoca sus
sesiones anteriores para que las credenciales actuales sean efectivas.

## Validación previa a la exposición

Ejecutar:

```powershell
docker compose --env-file .env.docker --profile demo run --rm demo-smoke
```

El control verifica:

- la SPA desde la URL pública;
- `/health` a través de Nginx;
- login de administrador y especialista;
- gestión administrativa de usuarios;
- historial del especialista;
- detalle consolidado;
- revisión humana;
- descarga autenticada de la imagen Petri y microscópica;
- ausencia de rutas físicas en cabeceras.

## Recorrido sugerido para la demostración

1. Iniciar sesión como `especialista-demo`.
2. Mostrar el dashboard y los tres casos preparados.
3. Abrir `DEMO-BB-001` y explicar la diferencia entre predicción automática y revisión confirmada.
4. Mostrar las dos imágenes protegidas en el detalle.
5. Abrir `DEMO-BB-002` para mostrar una corrección humana sin modificar la predicción original.
6. Abrir `DEMO-BB-003` y registrar una revisión en vivo.
7. Crear un análisis nuevo únicamente cuando se cuente con imágenes de respaldo verificadas.
8. Repetir que las categorías son preliminares, no taxonómicas y no diagnósticas.

## Estado, logs y reinicio

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=200 api worker frontend
docker compose --env-file .env.docker restart api worker frontend
```

Detener sin eliminar datos:

```bash
docker compose --env-file .env.docker stop
```

Volver a iniciar:

```bash
docker compose --env-file .env.docker start
```

Eliminar contenedores conservando volúmenes:

```bash
docker compose --env-file .env.docker down
```

**No usar `down -v`** salvo que se quiera eliminar definitivamente la base de
datos, sesiones e imágenes.

## Respaldo

Crear el directorio local:

```powershell
New-Item -ItemType Directory -Force backups
```

### Base de datos

```powershell
$pg = docker compose --env-file .env.docker ps -q postgres
docker compose --env-file .env.docker exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists > /tmp/blueberry.sql'
docker cp "${pg}:/tmp/blueberry.sql" backups/database.sql
```

### Imágenes almacenadas

```powershell
$api = docker compose --env-file .env.docker ps -q api
docker compose --env-file .env.docker exec -T api tar -czf /tmp/blueberry-storage.tar.gz -C /app/storage .
docker cp "${api}:/tmp/blueberry-storage.tar.gz" backups/storage.tar.gz
```

Conservar juntos `database.sql`, `storage.tar.gz`, el código fuente y una copia
segura de `.env.docker` fuera del repositorio.

## Restauración

1. Levantar solo PostgreSQL y esperar que esté saludable.
2. Copiar y restaurar la base de datos:

```powershell
$pg = docker compose --env-file .env.docker ps -q postgres
docker cp backups/database.sql "${pg}:/tmp/blueberry.sql"
docker compose --env-file .env.docker exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/blueberry.sql'
```

3. Restaurar las imágenes mediante un contenedor temporal:

```powershell
docker compose --env-file .env.docker run --rm --no-deps `
  -v "${PWD}/backups:/backup:ro" `
  api sh -c 'rm -rf /app/storage/* && tar -xzf /backup/storage.tar.gz -C /app/storage'
```

4. Iniciar el stack y ejecutar el smoke:

```powershell
docker compose --env-file .env.docker up -d api worker frontend
docker compose --env-file .env.docker --profile demo run --rm demo-smoke
```

## Paquete para demostración sin internet

Preparar en una máquina con internet:

```powershell
docker compose --env-file .env.docker build api worker migrate frontend
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker save -o backups/blueberry-offline-images.tar `
  blueberry-microid-backend:local `
  blueberry-microid-frontend:local `
  postgres:16-alpine `
  redis:7-alpine
```

Copiar a la máquina sin internet:

- repositorio o archivo ZIP del proyecto;
- `.env.docker` protegido;
- `blueberry-offline-images.tar`;
- respaldo opcional de base de datos e imágenes.

Cargar y arrancar sin reconstruir:

```powershell
docker load -i backups/blueberry-offline-images.tar
docker compose --env-file .env.docker up -d --no-build postgres redis migrate api worker frontend
docker compose --env-file .env.docker --profile demo run --rm --no-deps demo-seed
docker compose --env-file .env.docker --profile demo run --rm --no-deps demo-smoke
```

El seed y el smoke están incluidos en la imagen backend; no descargan archivos,
modelos ni datasets externos.

## Límites y seguridad

- Nginx es el único servicio publicado al host.
- Las imágenes se obtienen mediante endpoints bearer protegidos; sus rutas físicas no se serializan.
- En `ENVIRONMENT=production` no existen Swagger, ReDoc ni OpenAPI públicos.
- El despliegue externo debe añadir TLS/HTTPS antes de transmitir tokens bearer.
- Las imágenes sintéticas solo demuestran el funcionamiento técnico; no prueban precisión científica.

# Autenticación y roles del MVP

BlueberryMicroID utiliza sesiones bearer opacas y revocables. La contraseña se
verifica con Argon2 mediante `pwdlib`; el servidor entrega al cliente un token
de alta entropía y conserva únicamente su hash SHA-256.

## Preparación inicial

1. Aplicar las migraciones:

```bash
alembic upgrade head
```

2. Crear el primer administrador sin credenciales predeterminadas:

```bash
python scripts/create_admin.py
```

El comando solicita usuario y contraseña de manera interactiva. Para una
automatización controlada puede leer:

```text
BLUEBERRY_ADMIN_USERNAME
BLUEBERRY_ADMIN_PASSWORD
```

La contraseña debe contener al menos 12 caracteres. Estas variables no deben
registrarse en el repositorio ni imprimirse en logs.

## Roles

| Rol | Capacidades |
| --- | --- |
| `specialist` | Muestras, imágenes, análisis, historial, detalle y revisión humana. |
| `admin` | Todas las capacidades de especialista, gestión de usuarios y rutas técnicas de modelos, datasets, auditoría y entrenamiento experimental. |

La matriz completa está en
[`docs/security/access_control_matrix.md`](../security/access_control_matrix.md).

## Inicio de sesión

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
```

Campos:

- `username`
- `password`

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=REEMPLAZAR"
```

Respuesta:

```json
{
  "access_token": "token-opaco-entregado-una-sola-vez",
  "token_type": "bearer",
  "expires_at": "2026-07-31T16:00:00Z",
  "user": {
    "id": "2f95ec20-27b4-4c55-bc03-a7d7e739e8a0",
    "username": "admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-07-31T04:00:00Z",
    "updated_at": "2026-07-31T04:00:00Z"
  }
}
```

Las credenciales inválidas, usuarios inexistentes e inactivos producen el
mismo error genérico `invalid_credentials`.

## Uso del token

```http
Authorization: Bearer <access_token>
```

Ejemplo:

```bash
curl http://127.0.0.1:8000/api/v1/analysis-runs \
  -H "Authorization: Bearer $TOKEN"
```

La duración se configura con `AUTH_SESSION_TTL_HOURS`; el valor predeterminado
es 12 horas y el rango permitido es de 1 a 168 horas.

## Perfil actual

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

Devuelve la identidad y el rol, pero nunca el hash de contraseña ni el hash del
token.

## Cierre de sesión

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

La sesión actual se revoca de forma persistente. El mismo token recibe `401`
en solicitudes posteriores.

## Administración de usuarios

Todas estas rutas requieren rol `admin`.

### Crear usuario

```http
POST /api/v1/admin/users
```

```json
{
  "username": "especialista1",
  "password": "contraseña-larga-y-segura",
  "role": "specialist"
}
```

### Listar usuarios

```http
GET /api/v1/admin/users
```

### Actualizar usuario

```http
PATCH /api/v1/admin/users/{user_id}
```

Se puede modificar uno o varios campos:

```json
{
  "role": "specialist",
  "is_active": false,
  "password": "nueva-contraseña-larga"
}
```

Cambiar contraseña, rol o estado revoca todas las sesiones activas del usuario.
El sistema impide desactivar o degradar al último administrador activo.

## Respuestas de autorización

| HTTP | Código | Significado |
| --- | --- | --- |
| `401` | `invalid_credentials` | Login incorrecto o usuario inactivo. |
| `401` | `authentication_required` | Token ausente, desconocido, expirado, revocado o perteneciente a un usuario inactivo. |
| `403` | `permission_denied` | La sesión es válida, pero el rol no permite la operación. |
| `409` | `duplicate_username` | El nombre normalizado ya existe. |
| `409` | `last_active_admin` | La operación eliminaría al último administrador activo. |

Las respuestas `401` incluyen `WWW-Authenticate: Bearer`.

## Producción

Cuando `ENVIRONMENT=production`, FastAPI deshabilita `/docs`, `/redoc` y
`/openapi.json`. El despliegue debe terminar TLS/HTTPS antes de exponer la API;
un token bearer no debe circular por HTTP sin cifrado.

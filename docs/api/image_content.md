# Acceso protegido al contenido de imágenes

El detalle consolidado devuelve metadatos seguros e identificadores, pero nunca
el campo `file_path`. El contenido binario se obtiene mediante rutas separadas
y autenticadas.

## Caja Petri

```http
GET /api/v1/petri-images/{petri_image_id}/content
Authorization: Bearer <access_token>
```

## Microscopía

```http
GET /api/v1/micro-images/{micro_image_id}/content
Authorization: Bearer <access_token>
```

Ambas rutas aceptan sesiones con rol `specialist` o `admin` y responden con:

- bytes originales almacenados;
- `Content-Type` persistido para la imagen;
- `Content-Disposition: inline` con el nombre base seguro;
- `Cache-Control: private`;
- `X-Content-Type-Options: nosniff`.

No se incluyen rutas físicas en JSON, cabeceras ni mensajes de error.

## Validación del almacenamiento

Antes de leer un archivo, el adaptador resuelve su ruta y comprueba que
permanezca dentro de uno de los directorios configurados:

- `STORAGE_ROOT`;
- `BLUEBERRY_MICROID_UPLOAD_STORAGE_DIR`.

Una ruta fuera de esos directorios, un archivo eliminado o un error de lectura
produce:

```json
{
  "error": {
    "code": "stored_image_unavailable",
    "message": "Stored image content is unavailable",
    "request_id": "..."
  }
}
```

con `HTTP 404`. La respuesta deliberadamente no distingue entre archivo
inexistente y ruta persistida no autorizada, evitando revelar estructura del
servidor.

Un identificador que no existe conserva los errores controlados existentes:

- `petri_image_not_found`;
- `micro_image_not_found`.

## Uso desde el frontend

Una etiqueta `<img src="...">` no puede adjuntar automáticamente el bearer
token. Por ello, la SPA solicita los bytes mediante `fetch`, crea un URL local
con `URL.createObjectURL` y lo revoca cuando el componente se desmonta.

Ante un `401`, el cliente elimina la sesión local. Ante un `404`, muestra
`Imagen no disponible` sin renderizar una imagen rota ni exponer información
interna.

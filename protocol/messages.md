# Protocolo WebSocket

El móvil se conecta al puerto `8765` del ordenador mediante WebSocket seguro (`wss://`). Cada mensaje es un objeto JSON UTF-8 dentro de un canal TLS.

| Dirección | Tipo | Campos |
| --- | --- | --- |
| Ordenador → móvil | `remote_mouse` | `version`, `name`, `pairing_required` |
| Móvil → ordenador | `pair` | `code` temporal de seis cifras |
| Ordenador → móvil | `pair_result` | `ok`, `reason` opcional |
| Móvil → ordenador | `move` | `dx`, `dy` numéricos |
| Móvil → ordenador | `move_end` | — |
| Móvil → ordenador | `click` | `button` opcional |
| Móvil → ordenador | `scroll` | `amount` entero |
| Móvil → ordenador | `media` | `action` |

Antes de ejecutar acciones, el móvil debe recibir un resultado `pair_result` correcto. El código se muestra en la aplicación de escritorio, rota cada cinco minutos y se incluye en el QR `mousephone://pair` para evitar teclearlo. El QR contiene el indicador TLS y la huella SHA-256 de la CA local. Antes de conectarse, el sistema operativo del móvil debe confiar en esa CA.

El esquema actual se mantiene en `schema.json`. La validación estricta del contenido de cada mensaje se implementará en la issue de seguridad correspondiente.

## Validación del servidor

Antes de procesar un mensaje, el servidor limita su tamaño a 16 KiB, rechaza campos no esperados y comprueba los tipos y rangos. Los deltas de cursor se limitan a ±500, el scroll a ±5000 y las acciones multimedia a la lista permitida. Los sobres cifrados exigen un contador positivo y creciente, por lo que los mensajes repetidos o manipulados no llegan a controlar Windows.

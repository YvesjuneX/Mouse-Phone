# Protocolo WebSocket

El móvil se conecta al puerto `8765` del ordenador mediante WebSocket. Cada mensaje es un objeto JSON UTF-8.

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

Antes de ejecutar acciones, el móvil debe recibir un resultado `pair_result` correcto. El código se muestra en la aplicación de escritorio, rota cada cinco minutos y se incluye en el QR `mousephone://pair` para evitar teclearlo. El QR no es aún una prueba criptográfica de identidad: TLS y el pinning del certificado se implementarán en la siguiente fase.

El esquema actual se mantiene en `schema.json`. La validación estricta del contenido de cada mensaje se implementará en la issue de seguridad correspondiente.

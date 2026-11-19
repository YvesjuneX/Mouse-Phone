# Protocolo WebSocket

El móvil se conecta al puerto `8765` del ordenador mediante WebSocket. Cada mensaje es un objeto JSON UTF-8.

| Dirección | Tipo | Campos |
| --- | --- | --- |
| Ordenador → móvil | `remote_mouse` | `version`, `name` |
| Móvil → ordenador | `move` | `dx`, `dy` numéricos |
| Móvil → ordenador | `move_end` | — |
| Móvil → ordenador | `click` | `button` opcional |
| Móvil → ordenador | `scroll` | `amount` entero |
| Móvil → ordenador | `media` | `action` |

El esquema actual se mantiene en `schema.json`. La validación estricta del contenido de cada mensaje se implementará en la issue de seguridad correspondiente.

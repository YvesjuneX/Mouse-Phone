# Mouse Phone

**Mouse Phone** convierte un teléfono móvil en un mando remoto para un ordenador Windows dentro de la misma red Wi-Fi. El proyecto está pensado como una demostración de comunicación en tiempo real entre una aplicación móvil y un servicio de escritorio.

## Funcionamiento actual

La aplicación del ordenador abre un servidor WebSocket local. La aplicación móvil busca ordenadores compatibles en la red Wi-Fi, permite guardar o añadir equipos por IP y establece una conexión con el ordenador seleccionado. Los movimientos y acciones del móvil se envían al servidor, que los traduce en acciones nativas de Windows.

El flujo de uso es el siguiente:

1. Se inicia el servicio en el ordenador.
2. Desde el móvil se busca un ordenador en la red o se añade su dirección IP.
3. El ordenador queda guardado para futuros usos.
4. Al seleccionarlo se abre el panel táctil y el móvil pasa a actuar como mando.

## Características

- Descubrimiento automático de ordenadores en la red local y conexión manual por IP.
- Lista persistente de ordenadores guardados en el móvil, con opción de eliminarlos mediante pulsación prolongada.
- Panel táctil para mover el cursor y toque para clic izquierdo.
- Movimiento del cursor interpolado en el ordenador para una respuesta fluida y estable.
- Barra lateral de desplazamiento con sensibilidad ajustada.
- Controles multimedia generales: reproducción/pausa, pista anterior, pista siguiente, volumen y saltos de −5/+5 segundos mediante las teclas de dirección.
- Interfaz adaptada a las zonas seguras de Android e iOS para evitar que el mando quede oculto bajo las barras del sistema.
- El servicio de escritorio reemplaza automáticamente una instancia anterior que estuviera usando su puerto.

## Arquitectura

| Componente | Tecnología | Responsabilidad |
| --- | --- | --- |
| `mobile-app` | React Native, TypeScript y Expo | Interfaz móvil, descubrimiento de equipos y envío de comandos. |
| `desktop-app` | Python y WebSockets | Servicio local, control del cursor y ejecución de comandos multimedia en Windows. |

La comunicación se realiza por WebSocket dentro de la red local. El servidor anuncia su identidad al conectarse el móvil; así la app distingue un equipo compatible de una dirección que simplemente tenga un puerto abierto. Antes de aceptar controles, el ordenador solicita un código temporal de seis cifras que puede introducirse o escanearse mediante QR.

## Alcance y seguridad

Es un prototipo para redes Wi-Fi de confianza. La conexión de control usa TLS y emparejamiento temporal. Para la primera conexión hay que instalar la CA local del ordenador en el almacén de confianza del móvil; consulta la guía local de despliegue. No debe exponerse a Internet ni usarse en redes públicas.

La guía de instalación, ejecución y resolución de incidencias se mantiene de forma local en `despliege.md` y no se publica en el repositorio.

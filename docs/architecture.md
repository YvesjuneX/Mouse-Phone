# Arquitectura

Mouse Phone contiene dos aplicaciones independientes: una app móvil en React Native/TypeScript y un servicio de escritorio en Python. No comparten código ejecutable: comparten únicamente el contrato de mensajes definido en `../protocol`.

## Dependencias

```text
Móvil: pantalla → funcionalidades → servicios
Escritorio: WebSocket → casos de uso → adaptadores de Windows
```

El servicio WebSocket no controla directamente el cursor; delega los comandos en `application`. A su vez, la capa de entrada encapsula las llamadas específicas de Windows. Esto permite probar la lógica sin mover el cursor real.

`App.tsx` y `server.py` se conservan como puntos de entrada compatibles. La lógica vive en `mobile-app/src` y `desktop-app/src/mouse_phone`.

# Remote Mouse: guía rápida de prueba

El ordenador y el móvil deben estar conectados a la misma red Wi-Fi. La primera configuración requiere Internet para descargar paquetes de Expo.

## 1. Iniciar el servidor del ordenador (Windows)

Abre PowerShell y ejecuta:

```powershell
cd C:\Users\juanl\Desktop\RemoteMouse\desktop-app
python server.py
```

Deja esta ventana abierta. Anota la IP que muestra, por ejemplo `192.168.1.129`. Si Windows pregunta, permite que Python se comunique en redes privadas.

Al ejecutar `python server.py`, el programa detecta y cierra una instancia anterior de Remote Mouse que esté usando el puerto `8765`, y después inicia la nueva versión. Si muestra que el puerto lo ocupa otro programa, cierra ese programa o cambia el puerto en el código.

## 2. Abrir la aplicación en el móvil

1. Instala **Expo Go** desde Google Play (Android) o App Store (iPhone).
2. Abre una segunda ventana de PowerShell y ejecuta:

   ```powershell
   cd C:\Users\juanl\Desktop\RemoteMouse\mobile-app
   npm.cmd install
   npm.cmd start -- --lan --clear
   ```

   Usa `npm.cmd`: en algunas configuraciones de Windows PowerShell bloquea el script `npm.ps1`.
3. Espera a que Expo muestre el código QR. Escanéalo desde Expo Go. Si la consola muestra una dirección `exp://...`, también puedes escribirla en Expo Go.
4. La pestaña **Ordenadores** inicia una búsqueda al abrirse. Cuando encuentra un equipo lo añade a la lista sin abrir el panel. También puedes buscar de nuevo con el botón inferior o añadir una IP con el botón `+` redondo de la esquina inferior derecha.
5. Los ordenadores añadidos o conectados se conservan en el móvil. Al conectar, pasa al **Panel táctil**: desliza un dedo para mover el cursor, toca para hacer clic y desliza por la barra lateral para usar la rueda. Los botones inferiores controlan reproducción, pista anterior/siguiente y volumen.

Si el móvil no se conecta, comprueba que ambos estén en la misma Wi-Fi y que el Firewall de Windows permita las conexiones privadas a Python. La detección automática busca el servidor dentro de la subred local.

## Versiones de Expo Go

El proyecto usa Expo SDK 58 para coincidir con Expo Go SDK 58. Si actualizas paquetes, detén Expo con `Ctrl+C` y vuelve a ejecutar `npm.cmd install` y `npm.cmd start -- --lan` desde `mobile-app`.

## Seguridad

Este prototipo no cifra el tráfico ni autentica clientes. Úsalo únicamente en una red Wi-Fi de confianza y detén el servidor cuando termines.

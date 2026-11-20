# Preparar TLS en el móvil

Mouse Phone usa una autoridad certificadora (CA) local creada por el ordenador. Se guarda fuera del repositorio, en:

```text
%LOCALAPPDATA%\MousePhone\certificates\mouse-phone-ca.crt
```

1. Inicia `python server.py` en el ordenador.
2. En la ventana de Mouse Phone, pulsa **Abrir certificado para el móvil**.
3. Transfiere únicamente `mouse-phone-ca.crt` al móvil mediante un medio de confianza, por ejemplo USB.
4. Instálalo como certificado de CA y verifica que la huella SHA-256 mostrada en la ventana coincide con el archivo que instalas.
5. Vuelve a abrir la aplicación y escanea el QR o introduce el código temporal.

No instales certificados recibidos por enlaces, mensajes o redes que no controles. La clave privada de la CA (`mouse-phone-ca-key.pem`) no debe abandonar el ordenador.

> Expo Go y algunos dispositivos Android pueden no aceptar CAs instaladas por el usuario. En ese caso, prueba con una compilación de desarrollo o una versión instalada de la aplicación que tenga habilitada la confianza en la CA local. No desactives la validación de certificados para evitar este requisito.

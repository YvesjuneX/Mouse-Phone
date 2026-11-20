# Seguridad

La comunicación de control utiliza WebSocket seguro (`wss://`) con TLS 1.2 o superior. El ordenador crea una CA local en el perfil del usuario y emite un certificado con la IP LAN actual como SAN. La clave privada nunca se guarda en el repositorio.

La CA debe instalarse y marcarse como confiable en el teléfono antes de la primera conexión. El código QR muestra su huella SHA-256 para que el usuario pueda verificar que instaló el certificado correcto. La autenticación temporal, la gestión de sesiones y la validación estricta de mensajes siguen gestionándose como tareas separadas.

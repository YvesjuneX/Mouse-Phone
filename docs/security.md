# Seguridad

Los comandos viajan dentro de sobres cifrados y autenticados con ChaCha20-Poly1305. Las claves se acuerdan por sesión con X25519 y HKDF. El QR comparte un secreto temporal de 256 bits; el modo manual confirma la sesión con un código corto derivado de ella.

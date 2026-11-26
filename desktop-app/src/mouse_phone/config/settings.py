"""Valores configurables del servicio de escritorio."""

PORT = 8765
SENSITIVITY = 4.0
ANIMATION_INTERVAL_SECONDS = 1 / 120
MEDIA_KEY_PRESS_SECONDS = 0.04

# Límites defensivos para que un equipo de la red local no pueda agotar el
# servidor con conexiones o mensajes. Son suficientemente altos para el uso
# normal de varios móviles a la vez.
MAX_OPEN_CONNECTIONS = 12
MAX_CONNECTIONS_PER_SOURCE = 3
MAX_NEW_CONNECTIONS_PER_MINUTE = 12
MAX_ACTIVE_SESSIONS = 6
PAIRING_TIMEOUT_SECONDS = 15
MAX_MESSAGES_PER_SECOND = 180

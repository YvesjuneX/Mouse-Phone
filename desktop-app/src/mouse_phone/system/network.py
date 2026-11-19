"""Utilidades de red independientes del transporte WebSocket."""
import socket


def local_ip() -> str:
    """Obtiene la IP LAN preferida sin enviar tráfico."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()

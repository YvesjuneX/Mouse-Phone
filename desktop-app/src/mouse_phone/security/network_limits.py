"""Límites de recursos para conexiones WebSocket no confiables."""
from collections import defaultdict, deque
import threading
import time


class ConnectionGuard:
    """Controla conexiones abiertas y aperturas recientes por origen."""

    def __init__(self, max_open: int, max_per_source: int, max_new_per_window: int,
                 window_seconds: float = 60, clock=time.monotonic):
        self.max_open = max_open
        self.max_per_source = max_per_source
        self.max_new_per_window = max_new_per_window
        self.window_seconds = window_seconds
        self.clock = clock
        self._lock = threading.Lock()
        self._open = 0
        self._open_by_source: dict[str, int] = defaultdict(int)
        self._recent_by_source: dict[str, deque[float]] = defaultdict(deque)

    def admit(self, source: str) -> bool:
        """Reserva un hueco de conexión si el origen no supera los límites."""
        now = self.clock()
        with self._lock:
            recent = self._recent_by_source[source]
            while recent and now - recent[0] >= self.window_seconds:
                recent.popleft()
            if len(recent) >= self.max_new_per_window:
                return False
            recent.append(now)
            if self._open >= self.max_open or self._open_by_source[source] >= self.max_per_source:
                return False
            self._open += 1
            self._open_by_source[source] += 1
            return True

    def release(self, source: str) -> None:
        """Libera una reserva realizada por :meth:`admit`."""
        with self._lock:
            if not self._open_by_source.get(source):
                return
            self._open -= 1
            self._open_by_source[source] -= 1
            if not self._open_by_source[source]:
                self._open_by_source.pop(source, None)


class MessageRateLimiter:
    """Evita que una única sesión monopolice el bucle de eventos."""

    def __init__(self, max_messages: int, window_seconds: float = 1, clock=time.monotonic):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.clock = clock
        self._messages: deque[float] = deque()

    def allow(self) -> bool:
        now = self.clock()
        while self._messages and now - self._messages[0] >= self.window_seconds:
            self._messages.popleft()
        if len(self._messages) >= self.max_messages:
            return False
        self._messages.append(now)
        return True

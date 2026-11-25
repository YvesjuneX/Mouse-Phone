"""Límites de intentos para el emparejamiento mediante código temporal."""
from dataclasses import dataclass, field
import threading
import time


@dataclass
class AttemptRecord:
    failures: list[float] = field(default_factory=list)
    locked_until: float = 0.0


@dataclass(frozen=True)
class AttemptResult:
    locked: bool
    delay_seconds: float = 0.0
    remaining_attempts: int = 0


class PairingRateLimiter:
    """Limita por IP y por la combinación IP/dispositivo para evitar evasiones."""
    def __init__(self, max_failures: int = 5, window_seconds: int = 300, lockout_seconds: int = 600, clock=time.monotonic):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self.clock = clock
        self._records: dict[str, AttemptRecord] = {}
        self._lock = threading.Lock()

    def _keys(self, source: str, device_id: str) -> tuple[str, str]:
        return (f"source:{source}", f"device:{source}:{device_id}")

    def _clean(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for key, record in list(self._records.items()):
            record.failures = [failure for failure in record.failures if failure > cutoff]
            if not record.failures and record.locked_until <= now:
                del self._records[key]

    def is_locked(self, source: str, device_id: str) -> bool:
        with self._lock:
            now = self.clock(); self._clean(now)
            return any(self._records.get(key, AttemptRecord()).locked_until > now for key in self._keys(source, device_id))

    def record_failure(self, source: str, device_id: str) -> AttemptResult:
        with self._lock:
            now = self.clock(); self._clean(now)
            records = [self._records.setdefault(key, AttemptRecord()) for key in self._keys(source, device_id)]
            if any(record.locked_until > now for record in records): return AttemptResult(locked=True)
            for record in records: record.failures.append(now)
            failures = max(len(record.failures) for record in records)
            if failures >= self.max_failures:
                for record in records: record.locked_until = now + self.lockout_seconds
                return AttemptResult(locked=True)
            return AttemptResult(locked=False, delay_seconds=min(0.25 * (2 ** (failures - 1)), 2.0), remaining_attempts=self.max_failures - failures)

    def reset(self, source: str, device_id: str) -> None:
        with self._lock:
            for key in self._keys(source, device_id): self._records.pop(key, None)

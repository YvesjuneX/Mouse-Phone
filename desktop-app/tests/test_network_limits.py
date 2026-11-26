import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.active_sessions import ActiveSessions
from mouse_phone.security.network_limits import ConnectionGuard, MessageRateLimiter


class NetworkLimitsTests(unittest.TestCase):
    def setUp(self):
        self.now = [1_000.0]

    def test_connection_guard_limits_global_and_source_connections(self):
        guard = ConnectionGuard(2, 1, 3, clock=lambda: self.now[0])
        self.assertTrue(guard.admit("phone-a"))
        self.assertFalse(guard.admit("phone-a"))
        self.assertTrue(guard.admit("phone-b"))
        self.assertFalse(guard.admit("phone-c"))
        guard.release("phone-a")
        self.assertTrue(guard.admit("phone-c"))

    def test_connection_guard_limits_new_connections_in_time_window(self):
        guard = ConnectionGuard(3, 3, 2, window_seconds=60, clock=lambda: self.now[0])
        self.assertTrue(guard.admit("phone")); guard.release("phone")
        self.assertTrue(guard.admit("phone")); guard.release("phone")
        self.assertFalse(guard.admit("phone"))
        self.now[0] += 61
        self.assertTrue(guard.admit("phone"))

    def test_message_limiter_recovers_after_its_window(self):
        limiter = MessageRateLimiter(2, clock=lambda: self.now[0])
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertFalse(limiter.allow())
        self.now[0] += 1.1
        self.assertTrue(limiter.allow())

    def test_active_sessions_refuse_new_sessions_after_capacity(self):
        sessions = ActiveSessions()
        first = sessions.register("one", "Phone one", object(), None, max_sessions=1)
        self.assertIsNotNone(first)
        self.assertIsNone(sessions.register("two", "Phone two", object(), None, max_sessions=1))
        sessions.unregister(first)
        self.assertIsNotNone(sessions.register("two", "Phone two", object(), None, max_sessions=1))

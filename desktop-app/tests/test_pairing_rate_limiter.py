import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.pairing_rate_limiter import PairingRateLimiter


class PairingRateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.now = [1_000.0]
        self.limiter = PairingRateLimiter(max_failures=3, window_seconds=60, lockout_seconds=120, clock=lambda: self.now[0])

    def test_locks_after_maximum_failures_and_unlocks_after_timeout(self):
        self.assertEqual(self.limiter.record_failure("192.168.1.2", "phone").remaining_attempts, 2)
        self.assertEqual(self.limiter.record_failure("192.168.1.2", "phone").remaining_attempts, 1)
        self.assertTrue(self.limiter.record_failure("192.168.1.2", "phone").locked)
        self.assertTrue(self.limiter.is_locked("192.168.1.2", "phone"))
        self.now[0] += 121
        self.assertFalse(self.limiter.is_locked("192.168.1.2", "phone"))

    def test_source_limit_cannot_be_bypassed_with_a_new_device_id(self):
        self.limiter.record_failure("192.168.1.2", "one")
        self.limiter.record_failure("192.168.1.2", "two")
        self.assertTrue(self.limiter.record_failure("192.168.1.2", "three").locked)
        self.assertTrue(self.limiter.is_locked("192.168.1.2", "another-device"))

    def test_success_resets_failed_attempts(self):
        self.limiter.record_failure("192.168.1.2", "phone")
        self.limiter.reset("192.168.1.2", "phone")
        self.assertFalse(self.limiter.record_failure("192.168.1.2", "phone").locked)

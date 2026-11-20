import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.pairing import PairingManager


class PairingManagerTests(unittest.TestCase):
    def setUp(self):
        self.now = 1_000.0
        self.manager = PairingManager(60, lambda: self.now)

    def test_code_has_six_digits_and_verifies_while_active(self):
        details = self.manager.current()
        self.assertRegex(details.code, r"^\d{6}$")
        self.assertTrue(self.manager.verify(details.code))
        self.assertFalse(self.manager.verify("000000" if details.code != "000000" else "000001"))

    def test_code_rotates_after_expiry_and_on_manual_renewal(self):
        first = self.manager.current()
        self.now += 60
        second = self.manager.current()
        self.assertNotEqual(first.expires_at, second.expires_at)
        self.now += 1
        renewed = self.manager.renew()
        self.assertGreater(renewed.expires_at, second.expires_at)

    def test_qr_secret_is_random_and_changes_when_code_is_renewed(self):
        first = self.manager.current().qr_secret
        second = self.manager.renew().qr_secret
        self.assertEqual(len(first), 32)
        self.assertNotEqual(first, second)

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.session_crypto import SecureSession, new_keypair, unb64


class SessionCryptoTests(unittest.TestCase):
    def test_encrypts_and_rejects_replay_or_tampering(self):
        private_a, public_a = new_keypair(); private_b, public_b = new_keypair()
        a, b = SecureSession(private_a, unb64(public_b), b"x" * 32), SecureSession(private_b, unb64(public_a), b"x" * 32)
        self.assertEqual(a.sas, b.sas)
        message = a.encrypt({"type": "move", "dx": 1})
        self.assertEqual(b.decrypt(message)["dx"], 1)
        with self.assertRaises(ValueError): b.decrypt(message)

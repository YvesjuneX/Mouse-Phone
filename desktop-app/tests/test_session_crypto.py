import sys
import unittest
from pathlib import Path
from cryptography.exceptions import InvalidTag

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

    def test_code_secret_rejects_an_incorrect_pairing_code(self):
        private_a, public_a = new_keypair(); private_b, public_b = new_keypair()
        valid = SecureSession(private_a, unb64(public_b), b"123456")
        server = SecureSession(private_b, unb64(public_a), b"123456")
        incorrect = SecureSession(private_a, unb64(public_b), b"654321")
        self.assertEqual(server.decrypt(valid.encrypt({"type": "confirm"}))["type"], "confirm")
        fresh_server = SecureSession(private_b, unb64(public_a), b"123456")
        with self.assertRaises(InvalidTag): fresh_server.decrypt(incorrect.encrypt({"type": "confirm"}))

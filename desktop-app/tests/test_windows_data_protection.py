import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.device_registry import DeviceRegistry
from mouse_phone.security.windows_data_protection import protect, unprotect


@unittest.skipUnless(os.name == "nt", "Windows DPAPI requiere Windows")
class WindowsDataProtectionTests(unittest.TestCase):
    def test_round_trip_is_user_bound_encrypted_data(self):
        protected = protect(b"secret-token")
        self.assertNotEqual(protected, b"secret-token")
        self.assertEqual(unprotect(protected), b"secret-token")

    def test_registry_migrates_plaintext_data_to_a_protected_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devices.json"
            path.write_text(json.dumps({"temporary_minutes": 30, "devices": {"phone": {"name": "Teléfono", "state": "trusted", "token": "sensitive-token"}}}), encoding="utf-8")
            registry = DeviceRegistry(path)
            stored = path.read_text(encoding="utf-8")
            self.assertNotIn("sensitive-token", stored)
            self.assertIn("protected_data", stored)
            self.assertEqual(registry.list_devices()[0][0], "phone")

    def test_registry_recovers_safely_from_corrupted_protected_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devices.json"
            path.write_text(json.dumps({"version": 2, "protected_data": "not-valid-base64"}), encoding="utf-8")
            registry = DeviceRegistry(path)
            self.assertEqual(registry.list_devices(), [])

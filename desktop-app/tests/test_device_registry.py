import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.device_registry import DeviceRegistry


class DeviceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = DeviceRegistry(Path(self.tmp.name) / "devices.json")
    def tearDown(self): self.tmp.cleanup()
    def test_temporary_access_expires_and_blocking_revokes_access(self):
        self.registry.set_temporary_minutes(1)
        token = self.registry.register_temporary("phone", "Teléfono")
        self.assertEqual(self.registry.authorize("phone"), token)
        self.registry.set_state("phone", "blocked")
        self.assertIsNone(self.registry.authorize("phone"))

    def test_changing_temporary_duration_updates_existing_access(self):
        now = [1_000.0]
        registry = DeviceRegistry(Path(self.tmp.name) / "clocked.json", clock=lambda: now[0])
        token = registry.register_temporary("phone", "Teléfono")
        registry.set_temporary_minutes(1)
        now[0] += 61
        self.assertIsNone(registry.authorize("phone"))
        self.assertIsNotNone(token)
    def test_trusted_access_persists_across_registry_restarts(self):
        token = self.registry.register_temporary("phone", "Teléfono")
        self.registry.set_state("phone", "trusted")
        restarted = DeviceRegistry(self.registry.path)
        self.assertEqual(restarted.authorize("phone"), token)

    def test_revoking_a_temporary_device_requires_new_pairing(self):
        self.registry.register_temporary("phone", "Teléfono")
        self.assertTrue(self.registry.revoke_temporary("phone"))
        self.assertIsNone(self.registry.authorize("phone"))
        self.assertFalse(self.registry.revoke_temporary("unknown"))

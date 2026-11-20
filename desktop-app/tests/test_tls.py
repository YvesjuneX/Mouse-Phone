import asyncio
import ssl
import sys
import tempfile
import unittest
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.tls import create_server_context, ensure_tls_material


class TlsTests(unittest.TestCase):
    def test_creates_local_ca_and_a_tls_server_that_a_trusting_client_can_use(self):
        with tempfile.TemporaryDirectory() as directory:
            material = ensure_tls_material("127.0.0.1", Path(directory))
            self.assertTrue(material.ca_certificate.exists())
            self.assertTrue(material.certificate.exists())
            self.assertTrue(material.private_key.exists())
            self.assertRegex(material.ca_fingerprint, r"^[0-9A-F]{64}$")
            asyncio.run(self._handshake(material))

    async def _handshake(self, material):
        async def echo(websocket):
            await websocket.send("encrypted")
        async with websockets.serve(echo, "127.0.0.1", 0, ssl=create_server_context(material)) as server:
            port = server.sockets[0].getsockname()[1]
            client_context = ssl.create_default_context(cafile=material.ca_certificate)
            async with websockets.connect(f"wss://127.0.0.1:{port}", ssl=client_context) as websocket:
                self.assertEqual(await websocket.recv(), "encrypted")

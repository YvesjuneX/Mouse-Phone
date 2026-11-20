"""Sesiones cifradas de extremo a extremo para el protocolo local."""
import base64
import hashlib
import hmac
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def b64(value: bytes) -> str: return base64.b64encode(value).decode("ascii")
def unb64(value: str) -> bytes: return base64.b64decode(value.encode("ascii"), validate=True)


class SecureSession:
    def __init__(self, private: X25519PrivateKey, peer_public: bytes, extra_secret: bytes = b""):
        shared = private.exchange(X25519PublicKey.from_public_bytes(peer_public))
        self.key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"mouse-phone/session/v1" + extra_secret).derive(shared)
        self.box, self.sent, self.received = ChaCha20Poly1305(self.key), 0, -1

    @property
    def sas(self) -> str:
        return f"{int.from_bytes(hmac.new(self.key, b'mouse-phone/sas/v1', hashlib.sha256).digest()[:4], 'big') % 1_000_000:06d}"

    def encrypt(self, message: dict) -> dict:
        self.sent += 1
        nonce = os.urandom(12)
        data = self.box.encrypt(nonce, json.dumps(message, separators=(",", ":")).encode(), None)
        return {"type": "secure", "counter": self.sent, "nonce": b64(nonce), "data": b64(data)}

    def decrypt(self, envelope: dict) -> dict:
        counter = envelope["counter"]
        if not isinstance(counter, int) or counter <= self.received: raise ValueError("replayed message")
        plaintext = self.box.decrypt(unb64(envelope["nonce"]), unb64(envelope["data"]), None)
        self.received = counter
        return json.loads(plaintext)


def new_keypair() -> tuple[X25519PrivateKey, str]:
    private = X25519PrivateKey.generate()
    return private, b64(private.public_key().public_bytes_raw())

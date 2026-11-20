"""Creación y carga de certificados TLS locales para Mouse Phone."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import os
from pathlib import Path
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


@dataclass(frozen=True)
class TlsMaterial:
    ca_certificate: Path
    certificate: Path
    private_key: Path
    ca_fingerprint: str


def default_certificate_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MousePhone" / "certificates"


def _write_private_key(path: Path, key) -> None:
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def _load_private_key(path: Path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def _create_ca(certificate_path: Path, key_path: Path) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Mouse Phone Local CA")])
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True).add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True, key_encipherment=False, data_encipherment=False, key_agreement=False, content_commitment=False, encipher_only=False, decipher_only=False), critical=True).sign(key, hashes.SHA256()))
    _write_private_key(key_path, key)
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))


def ensure_tls_material(ip: str, directory: Path | None = None) -> TlsMaterial:
    """Conserva la CA y emite un certificado de servidor válido para la IP LAN actual."""
    directory = directory or default_certificate_dir()
    directory.mkdir(parents=True, exist_ok=True)
    ca_certificate, ca_key = directory / "mouse-phone-ca.crt", directory / "mouse-phone-ca-key.pem"
    certificate, private_key = directory / "mouse-phone-server.crt", directory / "mouse-phone-server-key.pem"
    if not ca_certificate.exists() or not ca_key.exists(): _create_ca(ca_certificate, ca_key)
    issuer_certificate = x509.load_pem_x509_certificate(ca_certificate.read_bytes())
    issuer_key = _load_private_key(ca_key)
    server_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Mouse Phone")])
    server_certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer_certificate.subject).public_key(server_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=365)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]), critical=False).add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True).add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False, key_cert_sign=False, crl_sign=False, key_agreement=True, data_encipherment=False, content_commitment=False, encipher_only=False, decipher_only=False), critical=True).sign(issuer_key, hashes.SHA256()))
    _write_private_key(private_key, server_key)
    certificate.write_bytes(server_certificate.public_bytes(serialization.Encoding.PEM))
    fingerprint = hashlib.sha256(ca_certificate.read_bytes()).hexdigest().upper()
    return TlsMaterial(ca_certificate, certificate, private_key, fingerprint)


def create_server_context(material: TlsMaterial) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(material.certificate, material.private_key)
    return context

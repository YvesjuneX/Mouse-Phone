import { x25519 } from '@noble/curves/ed25519.js';
import { chacha20poly1305 } from '@noble/ciphers/chacha.js';
import { hkdf } from '@noble/hashes/hkdf.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { hmac } from '@noble/hashes/hmac.js';
import { bytesToHex, utf8ToBytes } from '@noble/hashes/utils.js';
import { fromByteArray, toByteArray } from 'base64-js';
import * as ExpoCrypto from 'expo-crypto';

const info = utf8ToBytes('mouse-phone/session/v1');
const b64 = (data: Uint8Array) => fromByteArray(data);
const unb64 = (data: string) => toByteArray(data);
export const sessionCodeSecret = (code: string) => b64(utf8ToBytes(code));

export class SecureSession {
  private readonly key: Uint8Array; private sent = 0; private received = -1;
  constructor(privateKey: Uint8Array, peer: string, extra = '') {
    const shared = x25519.getSharedSecret(privateKey, unb64(peer));
    this.key = hkdf(sha256, shared, undefined, extra ? new Uint8Array([...info, ...unb64(extra)]) : info, 32);
  }
  get sas() { return String(parseInt(bytesToHex(hmac(sha256, this.key, utf8ToBytes('mouse-phone/sas/v1')).slice(0, 4)), 16) % 1_000_000).padStart(6, '0'); }
  encrypt(message: object) { this.sent++; const nonce = ExpoCrypto.getRandomBytes(12); return { type: 'secure', counter: this.sent, nonce: b64(nonce), data: b64(chacha20poly1305(this.key, nonce).encrypt(utf8ToBytes(JSON.stringify(message)))) }; }
  decrypt(envelope: any) { if (!Number.isInteger(envelope.counter) || envelope.counter <= this.received) throw new Error('Mensaje repetido'); const nonce = unb64(envelope.nonce); const value = JSON.parse(new TextDecoder().decode(chacha20poly1305(this.key, nonce).decrypt(unb64(envelope.data)))); this.received = envelope.counter; return value; }
}
export function newKeyPair() { const secretKey = ExpoCrypto.getRandomBytes(32); return { secretKey, publicKey: b64(x25519.getPublicKey(secretKey)) }; }

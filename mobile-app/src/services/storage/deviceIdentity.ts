import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const identityKey = 'mouse-phone.device-id';
export async function deviceId() { let id = await SecureStore.getItemAsync(identityKey); if (!id) { id = Crypto.randomUUID(); await SecureStore.setItemAsync(identityKey, id); } return id; }
// SecureStore only permits alphanumeric characters, dots, hyphens and underscores.
const credentialKey = (ip: string) => `mouse-phone.credential.${ip.replace(/[^a-zA-Z0-9._-]/g, '_')}`;
export const readCredential = (ip: string) => SecureStore.getItemAsync(credentialKey(ip));
export const saveCredential = (ip: string, token: string) => SecureStore.setItemAsync(credentialKey(ip), token);

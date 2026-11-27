import AsyncStorage from '@react-native-async-storage/async-storage';
import { COMPUTERS_STORAGE_KEY, LEGACY_COMPUTERS_STORAGE_KEY } from '../../config/constants';
import type { SavedComputer } from '../../features/computers/model';

export async function loadComputers(): Promise<SavedComputer[]> {
  const value = await AsyncStorage.getItem(COMPUTERS_STORAGE_KEY);
  if (value) return JSON.parse(value);
  const legacyValue = await AsyncStorage.getItem(LEGACY_COMPUTERS_STORAGE_KEY);
  if (!legacyValue) return [];
  await AsyncStorage.setItem(COMPUTERS_STORAGE_KEY, legacyValue);
  return JSON.parse(legacyValue);
}

export function saveComputers(computers: SavedComputer[]): Promise<void> {
  return AsyncStorage.setItem(COMPUTERS_STORAGE_KEY, JSON.stringify(computers));
}

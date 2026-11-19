import AsyncStorage from '@react-native-async-storage/async-storage';
import { COMPUTERS_STORAGE_KEY } from '../../config/constants';
import type { SavedComputer } from '../../features/computers/model';

export async function loadComputers(): Promise<SavedComputer[]> {
  const value = await AsyncStorage.getItem(COMPUTERS_STORAGE_KEY);
  return value ? JSON.parse(value) : [];
}

export function saveComputers(computers: SavedComputer[]): Promise<void> {
  return AsyncStorage.setItem(COMPUTERS_STORAGE_KEY, JSON.stringify(computers));
}

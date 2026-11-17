import * as SecureStore from 'expo-secure-store';
import type { Sesion } from './types';

const KEY = 'unab_sesion';

export async function guardarSesion(s: Sesion): Promise<void> {
  try {
    await SecureStore.setItemAsync(KEY, JSON.stringify(s));
  } catch {
    // ignorar
  }
}

export async function leerSesion(): Promise<Sesion | null> {
  try {
    const raw = await SecureStore.getItemAsync(KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Sesion;
    return s && s.codigo && s.pin ? s : null;
  } catch {
    return null;
  }
}

export async function borrarSesion(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(KEY);
  } catch {
    // ignorar
  }
}

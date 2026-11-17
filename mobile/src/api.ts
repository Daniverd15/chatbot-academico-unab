import Constants from 'expo-constants';
import type { ChatResponse, Credenciales, Dashboard, LoginResponse } from './types';

const extra = (Constants.expoConfig?.extra ?? {}) as { apiUrl?: string; apiKey?: string };
const API_URL = (extra.apiUrl ?? '').replace(/\/$/, '');
const API_KEY = extra.apiKey ?? '';
const TIMEOUT_MS = 75000;

export class ApiError extends Error {}

async function post<T>(path: string, body: object): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (res.status === 401 || res.status === 403) {
      throw new ApiError('No tienes autorización para usar el servicio. Revisa la configuración de la app.');
    }
    if (!res.ok) {
      throw new ApiError('El servicio no está disponible en este momento. Intenta de nuevo en unos minutos.');
    }
    const text = await res.text();
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new ApiError('Recibimos una respuesta inesperada del servidor. Intenta de nuevo.');
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof Error && e.name === 'AbortError') {
      throw new ApiError('La solicitud tardó demasiado. Revisa tu conexión e intenta de nuevo.');
    }
    throw new ApiError('No pudimos conectarnos. Revisa tu conexión a internet e intenta de nuevo.');
  } finally {
    clearTimeout(timer);
  }
}

export function login(c: Credenciales): Promise<LoginResponse> {
  return post<LoginResponse>('/app/login', c);
}

export function getDashboard(c: Credenciales): Promise<Dashboard> {
  return post<Dashboard>('/app/dashboard', c);
}

export function sendChat(c: Credenciales, mensaje: string): Promise<ChatResponse> {
  return post<ChatResponse>('/chat', { ...c, mensaje, session_id: c.codigo });
}

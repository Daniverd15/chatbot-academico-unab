import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Platform, StatusBar, useColorScheme, ViewStyle } from 'react-native';
import { guardarTema, leerTema } from './storage';

export const brand = {
  purple: '#8E00E6',
  orange: '#F7A600',
  navy: '#1C2B4A',
  teal: '#1F7A6E',
  surface: '#F7F7FB',
};

export interface Palette {
  bg: string;
  card: string;
  cardAlt: string;
  border: string;
  text: string;
  muted: string;
  primary: string;
  primarySoft: string;
  onPrimary: string;
  inputBg: string;
  skeleton: string;
  tabBar: string;
  shadow: string;
  navy: string;
  orange: string;
  teal: string;
  green: string;
  amber: string;
  red: string;
  blue: string;
  gray: string;
  gradient: [string, string];
}

export const lightPalette: Palette = {
  bg: brand.surface,
  card: '#FFFFFF',
  cardAlt: '#F1F2F8',
  border: '#E6E8F0',
  text: brand.navy,
  muted: '#6B7690',
  primary: brand.purple,
  primarySoft: '#F3E5FC',
  onPrimary: '#FFFFFF',
  inputBg: '#F1F2F8',
  skeleton: '#E6E8F0',
  tabBar: '#FFFFFF',
  shadow: '#1C2B4A',
  navy: brand.navy,
  orange: brand.orange,
  teal: brand.teal,
  green: '#1E9E5A',
  amber: '#E69A00',
  red: '#D63A3A',
  blue: '#2F6FE4',
  gray: '#8A93A6',
  gradient: [brand.purple, brand.navy],
};

export const darkPalette: Palette = {
  bg: '#0E1322',
  card: '#171F36',
  cardAlt: '#1F2842',
  border: '#27314E',
  text: '#EEF0F8',
  muted: '#9AA4BD',
  primary: '#B35CF0',
  primarySoft: '#2E1948',
  onPrimary: '#FFFFFF',
  inputBg: '#0F172B',
  skeleton: '#243051',
  tabBar: '#131A2E',
  shadow: '#000000',
  navy: '#27365C',
  orange: brand.orange,
  teal: '#35B3A2',
  green: '#35C47F',
  amber: '#F2B01E',
  red: '#F06262',
  blue: '#6C9BFF',
  gray: '#8791A8',
  gradient: ['#6A00AE', '#16223F'],
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 8, md: 14, lg: 20, xl: 28, pill: 999 };

export const fonts = {
  regular: 'Poppins_400Regular',
  medium: 'Poppins_500Medium',
  semibold: 'Poppins_600SemiBold',
  bold: 'Poppins_700Bold',
};

export const typography = {
  display: { fontFamily: fonts.bold, fontSize: 30, lineHeight: 38 },
  title: { fontFamily: fonts.bold, fontSize: 22, lineHeight: 30 },
  h2: { fontFamily: fonts.semibold, fontSize: 17, lineHeight: 24 },
  h3: { fontFamily: fonts.semibold, fontSize: 15, lineHeight: 22 },
  body: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 22 },
  bodyMedium: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 22 },
  small: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19 },
  caption: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 17 },
  label: { fontFamily: fonts.semibold, fontSize: 12, lineHeight: 16 },
  button: { fontFamily: fonts.semibold, fontSize: 16, lineHeight: 22 },
  number: { fontFamily: fonts.bold, fontSize: 40, lineHeight: 48 },
} as const;
export type TypeVariant = keyof typeof typography;

export function shadow(level: 0 | 1 | 2 | 3, c: Palette): ViewStyle {
  if (level === 0) return {};
  const dark = c.bg === darkPalette.bg;
  const o = dark ? 0.35 : [0, 0.06, 0.1, 0.16][level];
  return {
    shadowColor: c.shadow,
    shadowOffset: { width: 0, height: level * 2 },
    shadowOpacity: o,
    shadowRadius: level * 4,
    elevation: level * 2,
  };
}

export function alpha(hex: string, a: number): string {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

export const topInset = Platform.OS === 'android' ? (StatusBar.currentHeight ?? 24) : 44;

export function prioridadColor(c: Palette, p?: string): string {
  switch (p) {
    case 'ALTA':
      return c.red;
    case 'MEDIA':
      return c.amber;
    case 'BAJA':
      return c.blue;
    default:
      return c.gray;
  }
}

export function estadoAcademicoColor(c: Palette, estado?: string | null): string {
  const e = (estado ?? '').toLowerCase();
  if (e.includes('prueba')) return c.red;
  if (e.includes('condicional')) return c.amber;
  if (e === 'normal') return c.green;
  return c.gray;
}

export function estadoCursoColor(c: Palette, estado?: string): string {
  switch (estado) {
    case 'Aprobado':
      return c.green;
    case 'Cursando':
      return c.blue;
    case 'Reprobado (pendiente)':
      return c.red;
    default:
      return c.gray;
  }
}

export const ESTADOS_CURSO = ['Aprobado', 'Cursando', 'Reprobado (pendiente)', 'Pendiente'] as const;

export type ThemeMode = 'system' | 'light' | 'dark';

interface ThemeValue {
  c: Palette;
  dark: boolean;
  mode: ThemeMode;
  setMode: (m: ThemeMode) => void;
  ready: boolean;
}

const ThemeContext = createContext<ThemeValue>({
  c: lightPalette,
  dark: false,
  mode: 'system',
  setMode: () => undefined,
  ready: false,
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>('system');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    leerTema().then((m) => {
      if (m) setModeState(m);
      setReady(true);
    });
  }, []);

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m);
    guardarTema(m);
  }, []);

  const dark = mode === 'system' ? system === 'dark' : mode === 'dark';
  const value = useMemo<ThemeValue>(
    () => ({ c: dark ? darkPalette : lightPalette, dark, mode, setMode, ready }),
    [dark, mode, setMode, ready],
  );
  return React.createElement(ThemeContext.Provider, { value }, children);
}

export function useTheme(): ThemeValue {
  return useContext(ThemeContext);
}

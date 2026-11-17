import { Platform, StatusBar } from 'react-native';

export const colors = {
  orange: '#F7A600',
  purple: '#8E00E6',
  navy: '#1C2B4A',
  white: '#FFFFFF',
  bg: '#F4F5F9',
  border: '#E3E6EE',
  text: '#1C2B4A',
  muted: '#6B7690',
  green: '#1E9E5A',
  amber: '#E69A00',
  red: '#D63A3A',
  gray: '#8A93A6',
  blue: '#2F6FE4',
};

export const radius = { sm: 8, md: 14, lg: 20, pill: 999 };

export const topInset = Platform.OS === 'android' ? (StatusBar.currentHeight ?? 24) : 44;

export const prioridadColor: Record<string, string> = {
  ALTA: colors.red,
  MEDIA: colors.amber,
  BAJA: colors.blue,
  INFO: colors.gray,
};

export function estadoAcademicoColor(estado?: string | null): string {
  const e = (estado ?? '').toLowerCase();
  if (e.includes('prueba')) return colors.red;
  if (e.includes('condicional')) return colors.amber;
  if (e === 'normal') return colors.green;
  return colors.gray;
}

export const estadoCursoColor: Record<string, string> = {
  Aprobado: colors.green,
  Cursando: colors.blue,
  'Reprobado (pendiente)': colors.red,
  Pendiente: colors.gray,
};

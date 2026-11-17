import React from 'react';
import { Text, TextProps } from 'react-native';
import { TypeVariant, typography, useTheme } from '../theme';

interface Props extends TextProps {
  v?: TypeVariant;
  color?: string;
  muted?: boolean;
}

/** Texto tipado con las variantes del sistema de diseño (Poppins). */
export function Txt({ v = 'body', color, muted, style, ...rest }: Props) {
  const { c } = useTheme();
  return <Text {...rest} style={[typography[v], { color: color ?? (muted ? c.muted : c.text) }, style]} />;
}

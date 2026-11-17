import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { alpha, radius } from '../theme';
import { Txt } from './Txt';

interface Props {
  label: string;
  color: string;
  /** solid: fondo lleno con texto blanco. soft: fondo translúcido con texto de color. */
  solid?: boolean;
  icon?: keyof typeof Ionicons.glyphMap;
  small?: boolean;
}

export function Badge({ label, color, solid, icon, small }: Props) {
  const fg = solid ? '#FFFFFF' : color;
  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: solid ? color : alpha(color, 0.15), paddingVertical: small ? 2 : 4 },
      ]}
    >
      {icon ? <Ionicons name={icon} size={small ? 11 : 13} color={fg} style={{ marginRight: 4 }} /> : null}
      <Txt v="label" color={fg} style={small ? { fontSize: 11, lineHeight: 15 } : undefined}>
        {label}
      </Txt>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    borderRadius: radius.pill,
    alignSelf: 'flex-start',
  },
});

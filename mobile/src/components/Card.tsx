import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { alpha, radius, shadow, spacing, useTheme } from '../theme';
import { Txt } from './Txt';

interface Props {
  title?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  right?: React.ReactNode;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function Card({ title, icon, right, children, style }: Props) {
  const { c } = useTheme();
  return (
    <View style={[styles.card, shadow(1, c), { backgroundColor: c.card, borderColor: c.border }, style]}>
      {title ? (
        <View style={styles.head}>
          {icon ? (
            <View style={[styles.icon, { backgroundColor: alpha(c.primary, 0.12) }]}>
              <Ionicons name={icon} size={16} color={c.primary} />
            </View>
          ) : null}
          <Txt v="h2" style={{ flex: 1 }}>
            {title}
          </Txt>
          {right}
        </View>
      ) : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
  },
  head: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.md },
  icon: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginRight: spacing.sm },
});

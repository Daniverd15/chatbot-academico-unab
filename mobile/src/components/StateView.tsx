import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { alpha, radius, spacing, useTheme } from '../theme';
import { PressableScale } from './PressableScale';
import { Txt } from './Txt';

interface Props {
  icon?: keyof typeof Ionicons.glyphMap;
  title: string;
  message?: string;
  tone?: 'neutral' | 'error';
  onRetry?: () => void;
  retryLabel?: string;
}

/** Estado vacío o de error consistente, con botón de reintento opcional. */
export function StateView({ icon, title, message, tone = 'neutral', onRetry, retryLabel = 'Reintentar' }: Props) {
  const { c } = useTheme();
  const col = tone === 'error' ? c.red : c.primary;
  return (
    <View style={styles.wrap}>
      <View style={[styles.circle, { backgroundColor: alpha(col, 0.12) }]}>
        <Ionicons name={icon ?? (tone === 'error' ? 'cloud-offline-outline' : 'file-tray-outline')} size={34} color={col} />
      </View>
      <Txt v="h2" style={{ textAlign: 'center', marginTop: spacing.lg }}>
        {title}
      </Txt>
      {message ? (
        <Txt v="small" muted style={{ textAlign: 'center', marginTop: spacing.xs }}>
          {message}
        </Txt>
      ) : null}
      {onRetry ? (
        <PressableScale onPress={onRetry} style={[styles.btn, { backgroundColor: col }]} accessibilityRole="button">
          <Ionicons name="refresh" size={16} color="#fff" style={{ marginRight: 6 }} />
          <Txt v="label" color="#fff">
            {retryLabel}
          </Txt>
        </PressableScale>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', paddingVertical: spacing.xxl, paddingHorizontal: spacing.xl },
  circle: { width: 72, height: 72, borderRadius: 36, alignItems: 'center', justifyContent: 'center' },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    paddingVertical: 10,
    borderRadius: radius.pill,
    marginTop: spacing.lg,
  },
});

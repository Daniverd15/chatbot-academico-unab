import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '../theme';

export function ProgressBar({ percent, color = colors.purple }: { percent: number; color?: string }) {
  const p = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  return (
    <View style={styles.track}>
      <View style={[styles.fill, { width: `${p}%`, backgroundColor: color }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { height: 10, borderRadius: 5, backgroundColor: '#E8EAF2', overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 5 },
});

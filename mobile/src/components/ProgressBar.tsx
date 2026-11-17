import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import { useTheme } from '../theme';

interface Props {
  percent: number;
  color?: string;
  height?: number;
  trackColor?: string;
}

export function ProgressBar({ percent, color, height = 8, trackColor }: Props) {
  const { c } = useTheme();
  const p = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(v, { toValue: p, duration: 600, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
  }, [p, v]);
  const width = v.interpolate({ inputRange: [0, 100], outputRange: ['0%', '100%'] });
  return (
    <View style={[styles.track, { height, borderRadius: height / 2, backgroundColor: trackColor ?? c.skeleton }]}>
      <Animated.View style={{ width, height: '100%', borderRadius: height / 2, backgroundColor: color ?? c.primary }} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { overflow: 'hidden' },
});

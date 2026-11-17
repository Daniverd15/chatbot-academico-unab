import React, { useEffect, useRef } from 'react';
import { Animated, DimensionValue, StyleProp, View, ViewStyle } from 'react-native';
import { radius, shadow, spacing, useTheme } from '../theme';

export function Skeleton({
  width = '100%',
  height = 14,
  r = 8,
  style,
}: {
  width?: DimensionValue;
  height?: number;
  r?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const { c } = useTheme();
  const v = useRef(new Animated.Value(0.45)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(v, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(v, { toValue: 0.45, duration: 800, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [v]);
  return <Animated.View style={[{ width, height, borderRadius: r, backgroundColor: c.skeleton, opacity: v }, style]} />;
}

export function SkeletonCard({ lines = 3, height }: { lines?: number; height?: number }) {
  const { c } = useTheme();
  return (
    <View
      style={[
        { backgroundColor: c.card, borderRadius: radius.lg, padding: spacing.lg, marginBottom: spacing.lg, height },
        shadow(1, c),
      ]}
    >
      <Skeleton width="40%" height={16} style={{ marginBottom: spacing.md }} />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} width={i === lines - 1 ? '65%' : '100%'} style={{ marginBottom: spacing.sm }} />
      ))}
    </View>
  );
}

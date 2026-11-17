import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Stop } from 'react-native-svg';
import { brand } from '../theme';
import { Txt } from './Txt';

interface Props {
  percent: number;
  size?: number;
  stroke?: number;
}

/** Anillo de progreso animado (sobre fondo oscuro/degradado). */
export function ProgressRing({ percent, size = 128, stroke = 12 }: Props) {
  const p = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  const v = useRef(new Animated.Value(0)).current;
  const [shown, setShown] = useState(0);

  useEffect(() => {
    const id = v.addListener(({ value }) => setShown(value));
    Animated.timing(v, { toValue: p, duration: 1100, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
    return () => v.removeListener(id);
  }, [p, v]);

  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size}>
        <Defs>
          <LinearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={brand.orange} />
            <Stop offset="1" stopColor="#FFD36B" />
          </LinearGradient>
        </Defs>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,0.22)" strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="url(#ring)"
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${circ} ${circ}`}
          strokeDashoffset={circ * (1 - shown / 100)}
          rotation={-90}
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <View style={[StyleSheet.absoluteFill, styles.center]}>
        <Txt v="title" color="#fff" style={{ fontSize: 28, lineHeight: 34 }}>
          {Math.round(shown)}%
        </Txt>
        <Txt v="caption" color="rgba(255,255,255,0.8)">
          avance
        </Txt>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', justifyContent: 'center' },
});

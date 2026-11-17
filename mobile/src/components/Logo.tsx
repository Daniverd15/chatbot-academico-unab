import React from 'react';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';
import { brand } from '../theme';

/** Marca simple de UNABot: birrete sobre un tablero redondeado. */
export function Logo({ size = 72 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 80 80">
      <Defs>
        <LinearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor="#B04DFF" />
          <Stop offset="1" stopColor={brand.purple} />
        </LinearGradient>
      </Defs>
      <Rect x="2" y="2" width="76" height="76" rx="24" fill="url(#lg)" />
      <Rect x="2" y="2" width="76" height="76" rx="24" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="1.5" />
      <Path d="M40 20 L68 33 L40 46 L12 33 Z" fill="#FFFFFF" />
      <Path d="M24 41 V52 C24 57 32 61 40 61 C48 61 56 57 56 52 V41 L40 48 Z" fill="#FFFFFF" opacity="0.92" />
      <Path d="M66 35 V50" stroke={brand.orange} strokeWidth="3" strokeLinecap="round" />
      <Circle cx="66" cy="53" r="4" fill={brand.orange} />
    </Svg>
  );
}

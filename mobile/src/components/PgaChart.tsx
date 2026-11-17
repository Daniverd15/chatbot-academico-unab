import React, { useState } from 'react';
import { LayoutChangeEvent, View } from 'react-native';
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop, Text as SvgText } from 'react-native-svg';
import { fonts, useTheme } from '../theme';
import type { PgaPeriodo } from '../types';

const H = 190;
const PAD = { l: 34, r: 30, t: 24, b: 28 };

/** Gráfico de línea SVG del PGA por periodo, con referencias punteadas en 3.0 y 3.2. */
export function PgaChart({ data }: { data: PgaPeriodo[] }) {
  const { c } = useTheme();
  const [w, setW] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width);

  const pts = data.filter((d) => typeof d.pga_periodo === 'number' && Number.isFinite(d.pga_periodo));
  const vals = pts.map((d) => d.pga_periodo);
  const lo = Math.max(0, Math.floor((Math.min(...vals, 2.8) - 0.2) * 2) / 2);
  const hi = Math.min(5, Math.ceil((Math.max(...vals, 3.4) + 0.2) * 2) / 2);
  const iw = Math.max(1, w - PAD.l - PAD.r);
  const ih = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (pts.length <= 1 ? iw / 2 : (i * iw) / (pts.length - 1));
  const y = (v: number) => PAD.t + ih - ((v - lo) / (hi - lo)) * ih;
  const last = pts.length - 1;
  const anchor = (i: number): 'start' | 'middle' | 'end' => (pts.length > 1 && i === last ? 'end' : pts.length > 1 && i === 0 ? 'start' : 'middle');
  const anchorX = (i: number) => (anchor(i) === 'end' ? Math.min(x(i) + 6, w - 2) : anchor(i) === 'start' ? Math.max(x(i) - 6, 2) : x(i));
  const stride = Math.max(1, Math.ceil(pts.length / Math.max(1, Math.floor(iw / 52))));

  const line = pts.map((d, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)} ${y(d.pga_periodo).toFixed(1)}`).join(' ');
  const area = pts.length > 1 ? `${line} L${x(pts.length - 1).toFixed(1)} ${PAD.t + ih} L${x(0).toFixed(1)} ${PAD.t + ih} Z` : '';

  return (
    <View onLayout={onLayout} style={{ height: H }}>
      {w > 0 && pts.length > 0 ? (
        <Svg width={w} height={H}>
          <Defs>
            <LinearGradient id="area" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={c.primary} stopOpacity="0.28" />
              <Stop offset="1" stopColor={c.primary} stopOpacity="0" />
            </LinearGradient>
          </Defs>
          {[3.0, 3.2].map((ref) =>
            ref >= lo && ref <= hi ? (
              <React.Fragment key={ref}>
                <Line
                  x1={PAD.l}
                  x2={w - PAD.r}
                  y1={y(ref)}
                  y2={y(ref)}
                  stroke={ref === 3.0 ? c.red : c.amber}
                  strokeWidth={1.2}
                  strokeDasharray="5 4"
                />
                <SvgText x={PAD.l - 5} y={y(ref) + 3.5} fontSize={10} fontFamily={fonts.medium} fill={ref === 3.0 ? c.red : c.amber} textAnchor="end">
                  {ref.toFixed(1)}
                </SvgText>
              </React.Fragment>
            ) : null,
          )}
          <Line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={PAD.t + ih} stroke={c.border} strokeWidth={1} />
          <Line x1={PAD.l} x2={w - PAD.r} y1={PAD.t + ih} y2={PAD.t + ih} stroke={c.border} strokeWidth={1} />
          {area ? <Path d={area} fill="url(#area)" /> : null}
          {pts.length > 1 ? <Path d={line} stroke={c.primary} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" /> : null}
          {pts.map((d, i) => (
            <React.Fragment key={`${d.periodo_id}-${i}`}>
              <Circle cx={x(i)} cy={y(d.pga_periodo)} r={5} fill={c.card} stroke={c.primary} strokeWidth={2.5} />
              {i % stride === 0 || i === pts.length - 1 ? (
                <>
                  <SvgText x={anchorX(i)} y={y(d.pga_periodo) - 10} fontSize={11} fontFamily={fonts.semibold} fill={c.text} textAnchor={anchor(i)}>
                    {d.pga_periodo.toFixed(2)}
                  </SvgText>
                  <SvgText x={anchorX(i)} y={H - 8} fontSize={10} fontFamily={fonts.regular} fill={c.muted} textAnchor={anchor(i)}>
                    {String(d.periodo_id)}
                  </SvgText>
                </>
              ) : null}
            </React.Fragment>
          ))}
        </Svg>
      ) : null}
    </View>
  );
}

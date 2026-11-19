import React from 'react';
import { StyleSheet, View } from 'react-native';
import { alpha, radius, spacing, useTheme } from '../theme';
import type { FactorRiesgo } from '../types';
import { Txt } from './Txt';

interface Props {
  factores: FactorRiesgo[];
  explicacion?: string;
}

const fmtValor = (f: FactorRiesgo, v: number) => {
  if (f.feature === 'trabaja') return v >= 0.5 ? 'Sí' : 'No';
  return v.toFixed(f.feature === 'creditos_por_periodo' ? 1 : 2);
};

/**
 * Explicación del riesgo académico: barras divergentes desde un eje central.
 * Rojo (a la derecha) = el factor aumenta el riesgo; verde (a la izquierda) = lo reduce.
 * El ancho es proporcional a |contribución| en log-odds, relativo al factor de mayor peso.
 */
export function RiskFactors({ factores, explicacion }: Props) {
  const { c } = useTheme();
  if (!factores.length) return null;
  const max = Math.max(...factores.map((f) => Math.abs(f.contribucion)), 1e-6);

  return (
    <View>
      {explicacion ? (
        <Txt v="small" style={{ marginBottom: spacing.md }}>
          {explicacion}
        </Txt>
      ) : null}

      <View style={styles.axisLabels}>
        <Txt v="caption" color={c.green}>
          ← Reduce
        </Txt>
        <Txt v="caption" color={c.red}>
          Aumenta →
        </Txt>
      </View>

      {factores.map((f) => {
        const sube = f.contribucion > 0;
        const col = sube ? c.red : c.green;
        const pct = Math.max(2, (Math.abs(f.contribucion) / max) * 100);
        return (
          <View key={f.feature} style={styles.row} accessible accessibilityLabel={`${f.etiqueta}: ${sube ? 'aumenta' : 'reduce'} el riesgo. Tu valor ${fmtValor(f, f.valor)}, media del programa ${fmtValor(f, f.media)}`}>
            <View style={styles.rowHead}>
              <Txt v="label" style={{ flex: 1 }} numberOfLines={1}>
                {f.etiqueta}
              </Txt>
              <Txt v="caption" muted>
                Tú {fmtValor(f, f.valor)} · programa {fmtValor(f, f.media)}
              </Txt>
            </View>
            <View style={styles.track}>
              <View style={[styles.half, { alignItems: 'flex-end' }]}>
                {!sube ? <View style={[styles.bar, styles.barLeft, { width: `${pct}%`, backgroundColor: col }]} /> : null}
              </View>
              <View style={[styles.axis, { backgroundColor: c.border }]} />
              <View style={styles.half}>
                {sube ? <View style={[styles.bar, styles.barRight, { width: `${pct}%`, backgroundColor: col }]} /> : null}
              </View>
            </View>
            <View style={[styles.trackBg, { backgroundColor: alpha(c.gray, 0.08) }]} pointerEvents="none" />
          </View>
        );
      })}

      <Txt v="caption" muted style={{ marginTop: spacing.xs }}>
        Aporte de cada variable al modelo de regresión logística, comparada con la media del programa. Es orientativo, no una decisión automática.
      </Txt>
    </View>
  );
}

const BAR_H = 10;

const styles = StyleSheet.create({
  axisLabels: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing.xs },
  row: { marginBottom: spacing.md },
  rowHead: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  track: { flexDirection: 'row', alignItems: 'center', height: BAR_H + 4, zIndex: 1 },
  trackBg: { position: 'absolute', left: 0, right: 0, bottom: 0, height: BAR_H + 4, borderRadius: radius.sm },
  half: { flex: 1, height: BAR_H, justifyContent: 'center' },
  axis: { width: 2, height: BAR_H + 4 },
  bar: { height: BAR_H },
  barLeft: { borderTopLeftRadius: BAR_H / 2, borderBottomLeftRadius: BAR_H / 2 },
  barRight: { borderTopRightRadius: BAR_H / 2, borderBottomRightRadius: BAR_H / 2 },
});

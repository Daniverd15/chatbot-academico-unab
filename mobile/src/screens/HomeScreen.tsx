import React from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { ProgressBar } from '../components/ProgressBar';
import { colors, estadoAcademicoColor, prioridadColor } from '../theme';
import type { Dashboard } from '../types';

interface Props {
  nombre: string;
  data: Dashboard | null;
  loading: boolean;
  error: string | null;
  refreshing: boolean;
  onRefresh: () => void;
}

const fmt = (n: number | null | undefined, d = 2) => (typeof n === 'number' ? n.toFixed(d) : '—');

export function HomeScreen({ nombre, data, loading, error, refreshing, onRefresh }: Props) {
  const primer = (nombre || '').trim().split(/\s+/)[0] || '';
  const r = data?.resumen ?? null;
  const alertas = data?.alertas ?? [];
  const comps = data?.competencias ?? [];
  const proy = data?.proyeccion ?? null;
  const prob = proy?.proyeccion_probabilistica ?? null;
  const riesgo = data?.riesgo ?? null;
  const todasCompletas = comps.length >= 3 && comps.every((c) => c.cumplida);
  const pct = r?.porcentaje_avance ?? 0;

  const riesgoColor = riesgo?.nivel === 'alto' ? colors.red : riesgo?.nivel === 'medio' ? colors.amber : colors.green;

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[colors.purple]} />}
    >
      <Text style={styles.greeting}>¡Hola{primer ? `, ${primer}` : ''}!</Text>
      <Text style={styles.sub}>Este es el resumen de tu avance académico.</Text>

      {loading && !data ? <ActivityIndicator color={colors.purple} style={{ marginTop: 40 }} size="large" /> : null}
      {error ? (
        <Card style={{ borderColor: colors.red }}>
          <Text style={{ color: colors.red }}>{error}</Text>
          <Text style={styles.muted}>Desliza hacia abajo para reintentar.</Text>
        </Card>
      ) : null}

      {r ? (
        <Card title="Mi avance">
          <View style={styles.rowBetween}>
            <Text style={styles.bigPct}>{Math.round(pct)}%</Text>
            <Text style={styles.muted}>
              {r.creditos_aprobados ?? 0} / {r.creditos_totales ?? 0} créditos
            </Text>
          </View>
          <ProgressBar percent={pct} />
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Text style={styles.statLabel}>PGA acumulado</Text>
              <Text style={styles.statValue}>{fmt(r.pga_acumulado)}</Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statLabel}>Último periodo</Text>
              <Text style={styles.statValue}>{fmt(r.pga_ultimo_periodo)}</Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statLabel}>Semestre</Text>
              <Text style={styles.statValue}>{r.semestre_por_creditos ?? '—'}</Text>
            </View>
          </View>
          <View style={styles.badgesRow}>
            <View style={styles.badgeBlock}>
              <Text style={styles.statLabel}>Estado académico</Text>
              <Badge label={r.estado_academico || 'Sin dato'} color={estadoAcademicoColor(r.estado_academico)} />
            </View>
            <View style={styles.badgeBlock}>
              <Text style={styles.statLabel}>Matrícula actual</Text>
              <Text style={styles.matricula}>{r.estado_matricula_actual || 'Sin dato'}</Text>
            </View>
          </View>
          {riesgo ? (
            <View style={[styles.riskChip, { borderColor: riesgoColor }]}>
              <Ionicons name="warning-outline" size={16} color={riesgoColor} />
              <Text style={[styles.riskText, { color: riesgoColor }]}>
                Riesgo académico {riesgo.nivel} · {Math.round((riesgo.probabilidad ?? 0) * 100)}%
              </Text>
            </View>
          ) : null}
        </Card>
      ) : null}

      {alertas.length > 0 ? (
        <Card title="Alertas">
          {alertas.map((a, i) => (
            <View key={i} style={[styles.alert, { borderLeftColor: prioridadColor[a.prioridad] ?? colors.gray }]}>
              <Text style={[styles.alertPrio, { color: prioridadColor[a.prioridad] ?? colors.gray }]}>{a.prioridad}</Text>
              <Text style={styles.alertMsg}>{a.mensaje}</Text>
            </View>
          ))}
        </Card>
      ) : null}

      {comps.length > 0 ? (
        <Card title="Competencias digitales">
          {[...comps]
            .sort((a, b) => a.ruta - b.ruta)
            .map((c) => {
              const icon = c.cumplida ? 'checkmark-circle' : c.en_curso ? 'time' : 'ellipse-outline';
              const col = c.cumplida ? colors.green : c.en_curso ? colors.amber : colors.gray;
              const estado = c.cumplida ? 'Cumplida' : c.en_curso ? 'En curso' : 'Pendiente';
              return (
                <View key={c.ruta} style={styles.compRow}>
                  <Ionicons name={icon} size={24} color={col} />
                  <View style={{ flex: 1, marginLeft: 10 }}>
                    <Text style={styles.compName}>
                      Ruta {c.ruta}: {c.ruta_nombre}
                    </Text>
                    <Text style={styles.muted}>{c.detalle ? `${estado} · ${c.detalle}` : estado}</Text>
                  </View>
                </View>
              );
            })}
          <View style={[styles.insignia, { backgroundColor: todasCompletas ? colors.orange : colors.bg }]}>
            <Ionicons name="ribbon" size={20} color={todasCompletas ? colors.white : colors.gray} />
            <Text style={{ marginLeft: 8, fontWeight: '700', color: todasCompletas ? colors.white : colors.muted }}>
              {todasCompletas ? 'Insignia obtenida' : 'Insignia pendiente: completa las 3 rutas'}
            </Text>
          </View>
        </Card>
      ) : null}

      {proy ? (
        <Card title="Proyección de grado">
          <ProyRow label="Ideal" value={proy.periodo_grado_ideal} color={colors.green} />
          <ProyRow label="Probable (P50)" value={prob?.periodo_grado_p50} color={colors.amber} />
          <ProyRow label="Pesimista (P90)" value={prob?.periodo_grado_p90} color={colors.red} />
          {typeof proy.semestres_restantes_ideal === 'number' ? (
            <Text style={[styles.muted, { marginTop: 6 }]}>Semestres restantes (ideal): {proy.semestres_restantes_ideal}</Text>
          ) : null}
          {(prob?.cursos_con_mayor_riesgo_de_reprobar ?? []).length > 0 ? (
            <View style={{ marginTop: 12 }}>
              <Text style={styles.subTitle}>Cursos con mayor riesgo</Text>
              {(prob?.cursos_con_mayor_riesgo_de_reprobar ?? []).slice(0, 3).map((c, i) => (
                <View key={i} style={styles.rowBetween}>
                  <Text style={[styles.alertMsg, { flex: 1 }]}>{c.curso}</Text>
                  <Text style={{ color: colors.red, fontWeight: '700' }}>{Math.round((c.prob_reprobar ?? 0) * 100)}%</Text>
                </View>
              ))}
            </View>
          ) : null}
        </Card>
      ) : null}
    </ScrollView>
  );
}

function ProyRow({ label, value, color }: { label: string; value?: string; color: string }) {
  return (
    <View style={styles.proyRow}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.proyLabel}>{label}</Text>
      <Text style={styles.proyValue}>{value || '—'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  greeting: { fontSize: 24, fontWeight: '800', color: colors.navy },
  sub: { color: colors.muted, marginBottom: 16, marginTop: 2 },
  muted: { color: colors.muted, fontSize: 13 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  bigPct: { fontSize: 30, fontWeight: '800', color: colors.purple },
  statsRow: { flexDirection: 'row', marginTop: 14 },
  stat: { flex: 1 },
  statLabel: { fontSize: 12, color: colors.muted, marginBottom: 2 },
  statValue: { fontSize: 18, fontWeight: '700', color: colors.navy },
  badgesRow: { flexDirection: 'row', marginTop: 14 },
  badgeBlock: { flex: 1 },
  matricula: { fontSize: 14, fontWeight: '600', color: colors.navy },
  riskChip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderWidth: 1.5,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginTop: 14,
  },
  riskText: { marginLeft: 6, fontWeight: '700', fontSize: 13 },
  alert: { borderLeftWidth: 4, paddingLeft: 10, paddingVertical: 6, marginBottom: 8, backgroundColor: colors.bg, borderRadius: 6 },
  alertPrio: { fontSize: 11, fontWeight: '800' },
  alertMsg: { color: colors.navy, fontSize: 14 },
  compRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  compName: { fontWeight: '700', color: colors.navy, fontSize: 14 },
  insignia: { flexDirection: 'row', alignItems: 'center', padding: 10, borderRadius: 10, marginTop: 4 },
  proyRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  proyLabel: { flex: 1, color: colors.navy, fontSize: 14 },
  proyValue: { fontWeight: '700', color: colors.navy, fontSize: 15 },
  subTitle: { fontWeight: '700', color: colors.navy, marginBottom: 6 },
});

import React from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { PgaChart } from '../components/PgaChart';
import { ProgressRing } from '../components/ProgressRing';
import { SkeletonCard, Skeleton } from '../components/Skeleton';
import { StateView } from '../components/StateView';
import { FadeIn } from '../components/Transition';
import { Txt } from '../components/Txt';
import { alpha, estadoAcademicoColor, fonts, prioridadColor, radius, shadow, spacing, useTheme } from '../theme';
import type { Dashboard, Prioridad } from '../types';

interface Props {
  nombre: string;
  data: Dashboard | null;
  loading: boolean;
  error: string | null;
  refreshing: boolean;
  onRefresh: () => void;
  onRetry: () => void;
}

const fmt = (n: number | null | undefined, d = 2) => (typeof n === 'number' && Number.isFinite(n) ? n.toFixed(d) : '—');

const PRIO_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  ALTA: 'alert-circle',
  MEDIA: 'warning',
  BAJA: 'information-circle',
  INFO: 'bulb',
};
const PRIO_LABEL: Record<string, string> = { ALTA: 'Prioridad alta', MEDIA: 'Prioridad media', BAJA: 'Prioridad baja', INFO: 'Información' };

export function HomeScreen({ nombre, data, loading, error, refreshing, onRefresh, onRetry }: Props) {
  const { c } = useTheme();
  const primer = (nombre || '').trim().split(/\s+/)[0] || '';
  const r = data?.resumen ?? null;
  const alertas = data?.alertas ?? [];
  const comps = [...(data?.competencias ?? [])].sort((a, b) => a.ruta - b.ruta);
  const proy = data?.proyeccion ?? null;
  const prob = proy?.proyeccion_probabilistica ?? null;
  const riesgo = data?.riesgo ?? null;
  const historial = data?.historial_pga ?? [];
  const todasCompletas = comps.length >= 3 && comps.every((x) => x.cumplida);
  const pct = r?.porcentaje_avance ?? 0;
  const riesgoColor = riesgo?.nivel === 'alto' ? c.red : riesgo?.nivel === 'medio' ? c.amber : c.green;
  const riesgosCursos = prob?.cursos_con_mayor_riesgo_de_reprobar ?? [];

  const refresh = (
    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[c.primary]} tintColor={c.primary} progressBackgroundColor={c.card} />
  );

  return (
    <ScrollView style={{ flex: 1, backgroundColor: c.bg }} contentContainerStyle={styles.content} refreshControl={refresh} showsVerticalScrollIndicator={false}>
      <Txt v="title">¡Hola{primer ? `, ${primer}` : ''}!</Txt>
      <Txt v="small" muted style={{ marginBottom: spacing.lg }}>
        Este es el resumen de tu avance académico.
      </Txt>

      {loading && !data ? (
        <>
          <View style={[styles.heroSkel, { backgroundColor: c.card }, shadow(1, c)]}>
            <Skeleton width={128} height={128} r={64} />
            <View style={{ flex: 1, marginLeft: spacing.lg }}>
              <Skeleton width="50%" height={12} style={{ marginBottom: 10 }} />
              <Skeleton width="70%" height={34} style={{ marginBottom: 12 }} />
              <Skeleton width="45%" height={22} r={11} />
            </View>
          </View>
          <SkeletonCard lines={4} height={230} />
          <SkeletonCard lines={3} />
          <SkeletonCard lines={3} />
        </>
      ) : null}

      {!data && !loading && error ? <StateView tone="error" title="No pudimos cargar tu información" message={error} onRetry={onRetry} /> : null}
      {!data && !loading && !error ? <StateView icon="school-outline" title="Aún no hay datos" message="Desliza hacia abajo para actualizar." onRetry={onRetry} /> : null}

      {data && error ? (
        <View style={[styles.banner, { backgroundColor: alpha(c.red, 0.12), borderColor: alpha(c.red, 0.4) }]}>
          <Ionicons name="cloud-offline-outline" size={18} color={c.red} />
          <Txt v="caption" color={c.red} style={{ flex: 1, marginHorizontal: spacing.sm }}>
            {error}
          </Txt>
          <Txt v="label" color={c.red} onPress={onRetry}>
            Reintentar
          </Txt>
        </View>
      ) : null}

      {r ? (
        <FadeIn>
          <LinearGradient colors={c.gradient} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[styles.hero, shadow(2, c)]}>
            <View style={styles.heroTop}>
              <ProgressRing percent={pct} />
              <View style={{ flex: 1, marginLeft: spacing.lg }}>
                <Txt v="caption" color="rgba(255,255,255,0.75)">
                  PGA acumulado
                </Txt>
                <Txt v="number" color="#fff">
                  {fmt(r.pga_acumulado)}
                </Txt>
                <Badge label={r.estado_academico || 'Sin dato'} color={estadoAcademicoColor(c, r.estado_academico)} solid icon="ribbon-outline" />
                <Txt v="small" color="rgba(255,255,255,0.85)" style={{ marginTop: spacing.sm }}>
                  {r.creditos_aprobados ?? 0} / {r.creditos_totales ?? 0} créditos
                </Txt>
              </View>
            </View>
            <View style={styles.heroStats}>
              <Stat label="Último periodo" value={fmt(r.pga_ultimo_periodo)} />
              <View style={styles.sep} />
              <Stat label="Semestre" value={String(r.semestre_por_creditos ?? '—')} />
              <View style={styles.sep} />
              <Stat label="Matrícula" value={r.estado_matricula_actual || '—'} small />
            </View>
            {riesgo ? (
              <View style={[styles.risk, { backgroundColor: 'rgba(255,255,255,0.14)' }]}>
                <View style={[styles.riskDot, { backgroundColor: riesgoColor }]} />
                <Txt v="label" color="#fff">
                  Riesgo académico {riesgo.nivel} · {Math.round((riesgo.probabilidad ?? 0) * 100)}%
                </Txt>
              </View>
            ) : null}
          </LinearGradient>
        </FadeIn>
      ) : null}

      {historial.length > 0 ? (
        <FadeIn delay={80}>
          <Card title="Evolución del PGA" icon="trending-up">
            <PgaChart data={historial} />
            <View style={styles.legend}>
              <LegendLine color={c.red} label="Mínimo 3.0" />
              <LegendLine color={c.amber} label="Meta 3.2" />
            </View>
          </Card>
        </FadeIn>
      ) : null}

      {alertas.length > 0 ? (
        <FadeIn delay={120}>
          <Card title="Alertas" icon="notifications-outline">
            {alertas.map((a, i) => {
              const col = prioridadColor(c, a.prioridad);
              const p: Prioridad = a.prioridad;
              return (
                <View key={i} style={[styles.alert, { backgroundColor: alpha(col, 0.1), borderColor: alpha(col, 0.35), marginBottom: i === alertas.length - 1 ? 0 : spacing.sm }]}>
                  <View style={[styles.alertIcon, { backgroundColor: col }]}>
                    <Ionicons name={PRIO_ICON[p] ?? 'information-circle'} size={18} color="#fff" />
                  </View>
                  <View style={{ flex: 1, marginLeft: spacing.md }}>
                    <Txt v="label" color={col}>
                      {PRIO_LABEL[p] ?? 'Aviso'}
                    </Txt>
                    <Txt v="small">{a.mensaje}</Txt>
                  </View>
                </View>
              );
            })}
          </Card>
        </FadeIn>
      ) : null}

      {comps.length > 0 ? (
        <FadeIn delay={160}>
          <Card title="Competencias digitales" icon="laptop-outline">
            <View style={styles.stepper}>
              {comps.map((k, i) => {
                const col = k.cumplida ? c.green : k.en_curso ? c.amber : c.gray;
                const estado = k.cumplida ? 'Cumplida' : k.en_curso ? 'En curso' : 'Pendiente';
                return (
                  <View key={k.ruta} style={styles.step}>
                    <View style={styles.stepLine}>
                      <View style={[styles.connector, { backgroundColor: i === 0 ? 'transparent' : comps[i - 1].cumplida && k.cumplida ? c.green : c.border }]} />
                      <View style={[styles.stepCircle, { backgroundColor: k.cumplida ? col : alpha(col, 0.15), borderColor: col }]}>
                        {k.cumplida ? (
                          <Ionicons name="checkmark" size={18} color="#fff" />
                        ) : k.en_curso ? (
                          <Ionicons name="time" size={17} color={col} />
                        ) : (
                          <Txt v="label" color={col}>
                            {k.ruta}
                          </Txt>
                        )}
                      </View>
                      <View style={[styles.connector, { backgroundColor: i === comps.length - 1 ? 'transparent' : k.cumplida && comps[i + 1].cumplida ? c.green : c.border }]} />
                    </View>
                    <Txt v="label" style={{ textAlign: 'center', marginTop: spacing.sm }} numberOfLines={3}>
                      {k.ruta_nombre}
                    </Txt>
                    <Txt v="caption" color={col} style={{ textAlign: 'center', fontFamily: fonts.medium }}>
                      {estado}
                    </Txt>
                    {k.detalle ? (
                      <Txt v="caption" muted style={{ textAlign: 'center' }} numberOfLines={2}>
                        {k.detalle}
                      </Txt>
                    ) : null}
                  </View>
                );
              })}
            </View>
            <View style={[styles.insignia, { backgroundColor: todasCompletas ? c.orange : c.cardAlt }]}>
              <Ionicons name="ribbon" size={22} color={todasCompletas ? '#fff' : c.gray} />
              <Txt v="h3" color={todasCompletas ? '#fff' : c.muted} style={{ marginLeft: spacing.sm, flex: 1 }}>
                {todasCompletas ? 'Insignia obtenida' : 'Insignia pendiente: completa las 3 rutas'}
              </Txt>
            </View>
          </Card>
        </FadeIn>
      ) : null}

      {proy ? (
        <FadeIn delay={200}>
          <Card title="Proyección de grado" icon="flag-outline">
            <View style={styles.timeline}>
              <View style={[styles.tlLine, { backgroundColor: c.border }]} />
              <TlNode label="Ideal" value={proy.periodo_grado_ideal} color={c.green} />
              <TlNode label="Probable (P50)" value={prob?.periodo_grado_p50} color={c.amber} />
              <TlNode label="Pesimista (P90)" value={prob?.periodo_grado_p90} color={c.red} />
            </View>
            {typeof proy.semestres_restantes_ideal === 'number' ? (
              <Txt v="small" muted style={{ marginTop: spacing.md }}>
                Semestres restantes (ideal): {proy.semestres_restantes_ideal}
              </Txt>
            ) : null}
            {riesgosCursos.length > 0 ? (
              <View style={{ marginTop: spacing.lg }}>
                <Txt v="h3" style={{ marginBottom: spacing.sm }}>
                  Cursos con mayor riesgo
                </Txt>
                {riesgosCursos.slice(0, 3).map((k, i) => (
                  <View key={i} style={styles.riskRow}>
                    <Txt v="small" style={{ flex: 1 }}>
                      {k.curso}
                    </Txt>
                    <Badge label={`${Math.round((k.prob_reprobar ?? 0) * 100)}%`} color={c.red} small />
                  </View>
                ))}
              </View>
            ) : null}
          </Card>
        </FadeIn>
      ) : null}
    </ScrollView>
  );
}

function Stat({ label, value, small }: { label: string; value: string; small?: boolean }) {
  return (
    <View style={{ flex: 1, alignItems: 'center' }}>
      <Txt v="caption" color="rgba(255,255,255,0.7)">
        {label}
      </Txt>
      <Txt v={small ? 'label' : 'h2'} color="#fff" numberOfLines={1} style={small ? { marginTop: 3 } : undefined}>
        {value}
      </Txt>
    </View>
  );
}

function LegendLine({ color, label }: { color: string; label: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginRight: spacing.lg }}>
      <View style={{ width: 16, height: 0, borderTopWidth: 2, borderStyle: 'dashed', borderColor: color, marginRight: 6 }} />
      <Txt v="caption" muted>
        {label}
      </Txt>
    </View>
  );
}

function TlNode({ label, value, color }: { label: string; value?: string; color: string }) {
  const { c } = useTheme();
  return (
    <View style={{ flex: 1, alignItems: 'center' }}>
      <View style={[styles.tlDot, { backgroundColor: color, borderColor: c.card }]} />
      <Txt v="caption" muted style={{ marginTop: spacing.sm, textAlign: 'center' }}>
        {label}
      </Txt>
      <Txt v="h3" style={{ textAlign: 'center' }}>
        {value || '—'}
      </Txt>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  heroSkel: { flexDirection: 'row', alignItems: 'center', borderRadius: radius.xl, padding: spacing.lg, marginBottom: spacing.lg },
  hero: { borderRadius: radius.xl, padding: spacing.lg, marginBottom: spacing.lg },
  heroTop: { flexDirection: 'row', alignItems: 'center' },
  heroStats: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.12)',
  },
  sep: { width: StyleSheet.hairlineWidth, height: 28, backgroundColor: 'rgba(255,255,255,0.3)' },
  risk: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 6, marginTop: spacing.md },
  riskDot: { width: 9, height: 9, borderRadius: 5, marginRight: 8 },
  banner: { flexDirection: 'row', alignItems: 'center', borderRadius: radius.md, borderWidth: 1, padding: spacing.md, marginBottom: spacing.lg },
  legend: { flexDirection: 'row', marginTop: spacing.sm, justifyContent: 'center' },
  alert: { flexDirection: 'row', alignItems: 'center', borderRadius: radius.md, borderWidth: 1, padding: spacing.md },
  alertIcon: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  stepper: { flexDirection: 'row', alignItems: 'flex-start' },
  step: { flex: 1, alignItems: 'center', paddingHorizontal: 2 },
  stepLine: { flexDirection: 'row', alignItems: 'center', alignSelf: 'stretch' },
  connector: { flex: 1, height: 3, borderRadius: 2 },
  stepCircle: { width: 36, height: 36, borderRadius: 18, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  insignia: { flexDirection: 'row', alignItems: 'center', padding: spacing.md, borderRadius: radius.md, marginTop: spacing.lg },
  timeline: { flexDirection: 'row', alignItems: 'flex-start', paddingTop: 2 },
  tlLine: { position: 'absolute', left: '16%', right: '16%', top: 9, height: 3, borderRadius: 2 },
  tlDot: { width: 20, height: 20, borderRadius: 10, borderWidth: 3 },
  riskRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4 },
});

import React, { useState } from 'react';
import { LayoutAnimation, Linking, Platform, Pressable, RefreshControl, ScrollView, StyleSheet, UIManager, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { ProgressBar } from '../components/ProgressBar';
import { Skeleton, SkeletonCard } from '../components/Skeleton';
import { StateView } from '../components/StateView';
import { FadeIn } from '../components/Transition';
import { Txt } from '../components/Txt';
import { haptic } from '../haptics';
import { alpha, ESTADOS_CURSO, estadoCursoColor, radius, shadow, spacing, useTheme } from '../theme';
import type { Dashboard, RutaAutoaprendizaje } from '../types';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  try {
    UIManager.setLayoutAnimationEnabledExperimental(true);
  } catch {
    // ignorar
  }
}

interface Props {
  data: Dashboard | null;
  loading: boolean;
  error: string | null;
  refreshing: boolean;
  onRefresh: () => void;
  onRetry: () => void;
}

export function PlanScreen({ data, loading, error, refreshing, onRefresh, onRetry }: Props) {
  const { c } = useTheme();
  const [open, setOpen] = useState<Record<number, boolean>>({});
  const avance = [...(data?.avance ?? [])].sort((a, b) => a.semestre - b.semestre);

  const toggle = (n: number) => {
    haptic('select');
    LayoutAnimation.configureNext(LayoutAnimation.create(220, 'easeInEaseOut', 'opacity'));
    setOpen((o) => ({ ...o, [n]: !o[n] }));
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[c.primary]} tintColor={c.primary} progressBackgroundColor={c.card} />}
    >
      {data?.autoaprendizaje && data.autoaprendizaje.cursos_foco?.length ? <RutaCard ruta={data.autoaprendizaje} /> : null}

      <View style={styles.legend}>
        {ESTADOS_CURSO.map((k) => (
          <View key={k} style={{ marginRight: spacing.sm, marginBottom: spacing.sm }}>
            <Badge label={k} color={estadoCursoColor(c, k)} />
          </View>
        ))}
      </View>

      {loading && !data ? (
        <>
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
        </>
      ) : null}
      {!data && !loading && error ? <StateView tone="error" title="No pudimos cargar tu plan" message={error} onRetry={onRetry} /> : null}
      {data && avance.length === 0 ? <StateView icon="school-outline" title="Sin información del plan" message="Aún no hay información de tu plan de estudios." onRetry={onRetry} /> : null}

      {avance.map((s, idx) => {
        const cursos = s.cursos ?? [];
        const total = cursos.reduce((a, k) => a + (k.creditos ?? 0), 0);
        const aprob = cursos.filter((k) => k.estado === 'Aprobado').reduce((a, k) => a + (k.creditos ?? 0), 0);
        const pct = total > 0 ? (aprob / total) * 100 : 0;
        const done = total > 0 && aprob === total;
        const isOpen = !!open[s.semestre];
        const cuenta = (e: string) => cursos.filter((k) => k.estado === e).length;
        const chips = ESTADOS_CURSO.map((e) => ({ e, n: cuenta(e) })).filter((x) => x.n > 0);
        return (
          <FadeIn key={s.semestre} delay={Math.min(idx, 6) * 40}>
            <View style={[styles.section, shadow(1, c), { backgroundColor: c.card, borderColor: c.border }]}>
              <Pressable onPress={() => toggle(s.semestre)} style={styles.header} accessibilityRole="button" accessibilityState={{ expanded: isOpen }}>
                <View style={[styles.num, { backgroundColor: done ? c.green : alpha(c.primary, 0.14) }]}>
                  {done ? (
                    <Ionicons name="checkmark" size={20} color="#fff" />
                  ) : (
                    <Txt v="h2" color={c.primary}>
                      {s.semestre}
                    </Txt>
                  )}
                </View>
                <View style={{ flex: 1, marginHorizontal: spacing.md }}>
                  <Txt v="h3">Semestre {s.semestre}</Txt>
                  <Txt v="caption" muted>
                    {aprob} / {total} créditos aprobados
                  </Txt>
                  <View style={{ marginTop: 6 }}>
                    <ProgressBar percent={pct} height={6} color={done ? c.green : c.primary} />
                  </View>
                </View>
                <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={20} color={c.muted} />
              </Pressable>
              <View style={styles.chipsRow}>
                {chips.map(({ e, n }) => (
                  <View key={e} style={{ marginRight: 6, marginBottom: 4 }}>
                    <Badge label={`${n} ${e === 'Reprobado (pendiente)' ? 'reprobado' : e.toLowerCase()}`} color={estadoCursoColor(c, e)} small />
                  </View>
                ))}
              </View>
              {isOpen
                ? cursos.map((k, i) => {
                    const col = estadoCursoColor(c, k.estado);
                    return (
                      <View key={`${k.curso_id}-${i}`} style={[styles.course, { borderTopColor: c.border }]}>
                        <View style={[styles.bar, { backgroundColor: col }]} />
                        <View style={{ flex: 1 }}>
                          <Txt v="small" style={{ fontFamily: 'Poppins_500Medium' }}>
                            {k.curso}
                          </Txt>
                          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4 }}>
                            <Badge label={k.estado} color={col} small />
                            <Txt v="caption" muted style={{ marginLeft: spacing.sm }}>
                              {k.creditos} créditos
                            </Txt>
                          </View>
                        </View>
                        <Txt v="h3" color={typeof k.nota_aprobacion === 'number' ? c.text : c.gray}>
                          {typeof k.nota_aprobacion === 'number' ? k.nota_aprobacion.toFixed(1) : '—'}
                        </Txt>
                      </View>
                    );
                  })
                : null}
            </View>
          </FadeIn>
        );
      })}
      {loading && data ? <Skeleton width="100%" height={4} /> : null}
    </ScrollView>
  );
}

const TIPO_FOCO: Record<string, { label: string; color: (c: ReturnType<typeof useTheme>['c']) => string }> = {
  repitencia: { label: 'Repitencia', color: (c) => c.red },
  cursando: { label: 'En curso', color: (c) => c.blue },
  preparacion: { label: 'Próximo periodo', color: (c) => c.teal },
  refuerzo: { label: 'Refuerzo de base', color: (c) => c.amber },
};

const ICONO_RECURSO: Record<string, keyof typeof Ionicons.glyphMap> = {
  video: 'play-circle-outline',
  curso: 'school-outline',
  libro: 'book-outline',
  práctica: 'code-slash-outline',
};

function abrir(url: string) {
  haptic('select');
  Linking.openURL(url).catch(() => undefined);
}

function RutaCard({ ruta }: { ruta: RutaAutoaprendizaje }) {
  const { c } = useTheme();
  const [verMas, setVerMas] = useState(false);
  const toggle = () => {
    haptic('select');
    LayoutAnimation.configureNext(LayoutAnimation.create(220, 'easeInEaseOut', 'opacity'));
    setVerMas((v) => !v);
  };
  return (
    <FadeIn>
      <Card title="Mi ruta de autoaprendizaje" icon="compass-outline">
        <Txt v="small" muted>
          {ruta.semanas} semanas · {ruta.horas_semana} h/semana de estudio autónomo, priorizadas con tus datos.
        </Txt>

        {ruta.cursos_foco.map((f) => {
          const t = TIPO_FOCO[f.tipo] ?? { label: f.tipo, color: () => c.primary };
          const col = t.color(c);
          return (
            <View key={f.curso_id} style={[styles.foco, { borderTopColor: c.border }]}>
              <View style={styles.focoHead}>
                <View style={[styles.bar, { backgroundColor: col }]} />
                <View style={{ flex: 1 }}>
                  <Txt v="h3">{f.curso}</Txt>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginTop: 4 }}>
                    <View style={{ marginRight: 6, marginBottom: 4 }}>
                      <Badge label={t.label} color={col} small />
                    </View>
                    <Badge label={`${f.horas_semana} h/sem`} color={c.primary} icon="time-outline" small />
                  </View>
                </View>
              </View>
              <Txt v="caption" muted style={{ marginTop: 2 }}>
                Por qué: {f.motivo}
              </Txt>
              <Txt v="small" style={{ marginTop: spacing.xs }}>
                {f.objetivo}
              </Txt>
              {f.recursos.map((r) => (
                <Pressable
                  key={r.url}
                  onPress={() => abrir(r.url)}
                  accessibilityRole="link"
                  accessibilityLabel={`Abrir ${r.titulo}`}
                  style={({ pressed }) => [styles.recurso, { backgroundColor: pressed ? alpha(c.primary, 0.12) : c.cardAlt }]}
                >
                  <Ionicons name={ICONO_RECURSO[r.tipo] ?? 'link-outline'} size={18} color={c.primary} />
                  <View style={{ flex: 1, marginHorizontal: spacing.sm }}>
                    <Txt v="small" color={c.primary} style={{ fontFamily: 'Poppins_500Medium' }} numberOfLines={2}>
                      {r.titulo}
                    </Txt>
                    <Txt v="caption" muted numberOfLines={1}>
                      {[r.proveedor, r.tipo, r.idioma, r.horas ? `≈${r.horas} h` : null].filter(Boolean).join(' · ')}
                    </Txt>
                  </View>
                  <Ionicons name="open-outline" size={16} color={c.muted} />
                </Pressable>
              ))}
            </View>
          );
        })}

        <Pressable onPress={toggle} style={styles.verMas} accessibilityRole="button" accessibilityState={{ expanded: verMas }}>
          <Txt v="label" color={c.primary}>
            {verMas ? 'Ocultar estrategias y apoyo' : 'Cómo estudiar: estrategias, hitos y apoyo'}
          </Txt>
          <Ionicons name={verMas ? 'chevron-up' : 'chevron-down'} size={16} color={c.primary} style={{ marginLeft: 4 }} />
        </Pressable>

        {verMas ? (
          <View>
            {(ruta.consejos ?? []).map((t, i) => (
              <View key={`c${i}`} style={[styles.consejo, { backgroundColor: alpha(c.amber, 0.12) }]}>
                <Ionicons name="bulb-outline" size={16} color={c.amber} />
                <Txt v="small" style={{ flex: 1, marginLeft: spacing.sm }}>
                  {t}
                </Txt>
              </View>
            ))}
            <Txt v="h3" style={styles.sub}>
              Estrategias con evidencia
            </Txt>
            {ruta.estrategias.map((e) => (
              <View key={e.nombre} style={{ marginBottom: spacing.sm }}>
                <Txt v="small" style={{ fontFamily: 'Poppins_500Medium' }}>
                  {e.nombre}
                </Txt>
                <Txt v="caption" muted>
                  {e.como}
                </Txt>
              </View>
            ))}
            <Txt v="h3" style={styles.sub}>
              Hitos de autoevaluación
            </Txt>
            {ruta.hitos.map((h) => (
              <View key={h.semana} style={styles.hito}>
                <Badge label={`Sem ${h.semana}`} color={c.teal} small />
                <Txt v="caption" style={{ flex: 1, marginLeft: spacing.sm }}>
                  {h.hito}
                </Txt>
              </View>
            ))}
            <Txt v="h3" style={styles.sub}>
              Apoyo UNAB
            </Txt>
            {ruta.apoyo_unab.map((a) => (
              <View key={a.servicio} style={styles.hito}>
                <Ionicons name="people-outline" size={16} color={c.primary} />
                <Txt v="caption" style={{ flex: 1, marginLeft: spacing.sm }}>
                  <Txt v="caption" style={{ fontFamily: 'Poppins_600SemiBold' }}>
                    {a.servicio}:{' '}
                  </Txt>
                  {a.para}
                </Txt>
              </View>
            ))}
          </View>
        ) : null}
      </Card>
    </FadeIn>
  );
}

const styles = StyleSheet.create({
  foco: { borderTopWidth: StyleSheet.hairlineWidth, paddingTop: spacing.md, marginTop: spacing.md },
  focoHead: { flexDirection: 'row', alignItems: 'center' },
  recurso: { flexDirection: 'row', alignItems: 'center', borderRadius: radius.md, padding: spacing.sm, marginTop: spacing.sm },
  verMas: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: spacing.md, paddingVertical: spacing.sm },
  consejo: { flexDirection: 'row', alignItems: 'flex-start', borderRadius: radius.md, padding: spacing.sm, marginBottom: spacing.sm },
  sub: { marginTop: spacing.sm, marginBottom: spacing.sm },
  hito: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: spacing.sm },
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  legend: { flexDirection: 'row', flexWrap: 'wrap' },
  section: { borderRadius: radius.lg, borderWidth: StyleSheet.hairlineWidth, marginBottom: spacing.md, overflow: 'hidden' },
  header: { flexDirection: 'row', alignItems: 'center', padding: spacing.lg, paddingBottom: spacing.sm },
  num: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center' },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: spacing.lg, paddingBottom: spacing.sm },
  course: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderTopWidth: StyleSheet.hairlineWidth },
  bar: { width: 4, alignSelf: 'stretch', borderRadius: 2, marginRight: spacing.md },
});

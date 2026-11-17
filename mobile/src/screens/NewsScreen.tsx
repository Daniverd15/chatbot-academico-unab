import React, { useMemo, useState } from 'react';
import { Linking, Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { SkeletonCard } from '../components/Skeleton';
import { StateView } from '../components/StateView';
import { FadeIn } from '../components/Transition';
import { Txt } from '../components/Txt';
import { haptic } from '../haptics';
import { alpha, radius, spacing, useTheme } from '../theme';
import type { Dashboard, EventoCalendario } from '../types';

interface Props {
  data: Dashboard | null;
  loading: boolean;
  error: string | null;
  refreshing: boolean;
  onRefresh: () => void;
  onRetry: () => void;
}

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

function parseFecha(s?: string | null): Date | null {
  if (!s) return null;
  const d = new Date(s.length === 10 ? `${s}T00:00:00` : s);
  return isNaN(d.getTime()) ? null : d;
}

function fmtFecha(d: Date | null): string {
  return d ? `${d.getDate()} ${MESES[d.getMonth()].slice(0, 3).toLowerCase()} ${d.getFullYear()}` : '';
}

function diasEntre(a: Date, b: Date): number {
  const A = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime();
  const B = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime();
  return Math.round((B - A) / 86400000);
}

function relativa(d: Date | null): string {
  if (!d) return '';
  const n = diasEntre(d, new Date());
  if (n < 0) return fmtFecha(d);
  if (n === 0) return 'Hoy';
  if (n === 1) return 'Ayer';
  if (n < 7) return `Hace ${n} días`;
  if (n < 30) {
    const w = Math.floor(n / 7);
    return `Hace ${w} ${w === 1 ? 'semana' : 'semanas'}`;
  }
  if (n < 365) {
    const m = Math.floor(n / 30);
    return `Hace ${m} ${m === 1 ? 'mes' : 'meses'}`;
  }
  return fmtFecha(d);
}

export function NewsScreen({ data, loading, error, refreshing, onRefresh, onRetry }: Props) {
  const { c } = useTheme();
  const [seg, setSeg] = useState<'noticias' | 'calendario'>('noticias');
  const noticias = data?.noticias ?? [];

  const grupos = useMemo(() => {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const ev = (data?.calendario ?? [])
      .filter((e) => {
        const f = parseFecha(e.fecha_fin) ?? parseFecha(e.fecha_inicio);
        return !f || f >= hoy;
      })
      .sort((a, b) => (parseFecha(a.fecha_inicio)?.getTime() ?? 0) - (parseFecha(b.fecha_inicio)?.getTime() ?? 0));
    const out: { clave: string; titulo: string; items: EventoCalendario[] }[] = [];
    for (const e of ev) {
      const d = parseFecha(e.fecha_inicio);
      const clave = d ? `${d.getFullYear()}-${d.getMonth()}` : 'sin';
      let g = out.find((x) => x.clave === clave);
      if (!g) {
        g = { clave, titulo: d ? `${MESES[d.getMonth()]} ${d.getFullYear()}` : 'Sin fecha', items: [] };
        out.push(g);
      }
      g.items.push(e);
    }
    return out;
  }, [data?.calendario]);

  const tipoColor = (t?: string | null) => {
    const palette = [c.primary, c.blue, c.teal, c.orange, c.green];
    const s = (t ?? '').toLowerCase();
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 997;
    return palette[h % palette.length];
  };

  const faltan = (e: EventoCalendario): { texto: string; color: string } | null => {
    const ini = parseFecha(e.fecha_inicio);
    const fin = parseFecha(e.fecha_fin) ?? ini;
    if (!ini || !fin) return null;
    const hoy = new Date();
    const n = diasEntre(hoy, ini);
    if (n > 1) return { texto: `Faltan ${n} días`, color: n <= 7 ? c.amber : c.blue };
    if (n === 1) return { texto: 'Falta 1 día', color: c.amber };
    if (diasEntre(hoy, fin) >= 0) return { texto: n === 0 ? 'Es hoy' : 'En curso', color: c.green };
    return null;
  };

  const sinDatos = !data;
  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <View style={[styles.segRow, { backgroundColor: c.cardAlt }]}>
        {(['noticias', 'calendario'] as const).map((k) => {
          const on = seg === k;
          return (
            <Pressable
              key={k}
              style={[styles.seg, on && { backgroundColor: c.primary }]}
              onPress={() => {
                if (!on) haptic('select');
                setSeg(k);
              }}
            >
              <Ionicons name={k === 'noticias' ? 'newspaper-outline' : 'calendar-outline'} size={16} color={on ? '#fff' : c.muted} />
              <Txt v="label" color={on ? '#fff' : c.muted} style={{ marginLeft: 6 }}>
                {k === 'noticias' ? 'Noticias' : 'Calendario'}
              </Txt>
            </Pressable>
          );
        })}
      </View>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[c.primary]} tintColor={c.primary} progressBackgroundColor={c.card} />}
      >
        {loading && sinDatos ? (
          <>
            <SkeletonCard lines={3} />
            <SkeletonCard lines={3} />
          </>
        ) : null}
        {sinDatos && !loading && error ? <StateView tone="error" title="No pudimos cargar las novedades" message={error} onRetry={onRetry} /> : null}

        {!sinDatos && seg === 'noticias' ? (
          noticias.length === 0 ? (
            <StateView icon="newspaper-outline" title="Sin noticias por ahora" message="Cuando haya convocatorias o novedades las verás aquí." onRetry={onRetry} retryLabel="Actualizar" />
          ) : (
            noticias.map((n, i) => {
              const col = tipoColor(n.tipo);
              const rel = relativa(parseFecha(n.fecha_pub));
              return (
                <FadeIn key={i} delay={Math.min(i, 6) * 40}>
                  <Pressable onPress={() => n.url && Linking.openURL(n.url).catch(() => undefined)}>
                    <Card>
                      <View style={styles.rowBetween}>
                        {n.tipo ? <Badge label={n.tipo} color={col} /> : <View />}
                        {rel ? (
                          <Txt v="caption" muted>
                            {rel}
                          </Txt>
                        ) : null}
                      </View>
                      <Txt v="h3" style={{ marginTop: spacing.sm }}>
                        {n.titulo}
                      </Txt>
                      {n.resumen ? (
                        <Txt v="small" muted numberOfLines={3} style={{ marginTop: 4 }}>
                          {n.resumen}
                        </Txt>
                      ) : null}
                      {n.url ? (
                        <View style={styles.more}>
                          <Txt v="label" color={c.primary}>
                            Leer más
                          </Txt>
                          <Ionicons name="arrow-forward" size={14} color={c.primary} style={{ marginLeft: 4 }} />
                        </View>
                      ) : null}
                    </Card>
                  </Pressable>
                </FadeIn>
              );
            })
          )
        ) : null}

        {!sinDatos && seg === 'calendario' ? (
          grupos.length === 0 ? (
            <StateView icon="calendar-outline" title="Sin eventos próximos" message="No hay eventos próximos en el calendario académico." onRetry={onRetry} retryLabel="Actualizar" />
          ) : (
            grupos.map((g) => (
              <View key={g.clave} style={{ marginBottom: spacing.sm }}>
                <Txt v="h2" style={{ marginBottom: spacing.sm }}>
                  {g.titulo}
                </Txt>
                {g.items.map((e, i) => {
                  const ini = parseFecha(e.fecha_inicio);
                  const fin = parseFecha(e.fecha_fin);
                  const f = faltan(e);
                  const rango = ini && fin && diasEntre(ini, fin) > 0 ? `${fmtFecha(ini)} – ${fmtFecha(fin)}` : fmtFecha(ini ?? fin);
                  return (
                    <FadeIn key={i} delay={Math.min(i, 6) * 40}>
                      <Card style={{ marginBottom: spacing.md, padding: spacing.md }}>
                        <View style={{ flexDirection: 'row' }}>
                          <View style={[styles.date, { backgroundColor: alpha(c.orange, 0.15) }]}>
                            <Txt v="h2" color={c.orange} style={{ lineHeight: 24 }}>
                              {ini ? ini.getDate() : '—'}
                            </Txt>
                            <Txt v="caption" color={c.orange} style={{ textTransform: 'uppercase', fontSize: 10, lineHeight: 13 }}>
                              {ini ? MESES[ini.getMonth()].slice(0, 3) : ''}
                            </Txt>
                          </View>
                          <View style={{ flex: 1, marginLeft: spacing.md }}>
                            <Txt v="h3">{e.evento}</Txt>
                            {rango ? (
                              <Txt v="caption" muted>
                                {rango}
                              </Txt>
                            ) : null}
                            <View style={styles.tags}>
                              {e.categoria ? (
                                <View style={{ marginRight: 6, marginTop: 6 }}>
                                  <Badge label={e.categoria} color={c.orange} small />
                                </View>
                              ) : null}
                              {f ? (
                                <View style={{ marginTop: 6 }}>
                                  <Badge label={f.texto} color={f.color} icon="time-outline" small />
                                </View>
                              ) : null}
                            </View>
                          </View>
                        </View>
                      </Card>
                    </FadeIn>
                  );
                })}
              </View>
            ))
          )
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  segRow: { flexDirection: 'row', margin: spacing.lg, marginBottom: 0, borderRadius: radius.md, padding: 4 },
  seg: { flex: 1, flexDirection: 'row', paddingVertical: 8, alignItems: 'center', justifyContent: 'center', borderRadius: radius.md - 4 },
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  more: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.sm },
  date: { width: 52, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', paddingVertical: 6 },
  tags: { flexDirection: 'row', flexWrap: 'wrap' },
});

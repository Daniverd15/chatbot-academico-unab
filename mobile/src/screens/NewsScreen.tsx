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
import { alpha, fonts, radius, spacing, useTheme } from '../theme';
import type { Dashboard, EventoCalendario, Noticia, TemaNoticia } from '../types';

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
  // El dashboard serializa timestamptz como "2026-11-19 22:01:42+00:00" (con espacio): Hermes exige la "T".
  const iso = s.length === 10 ? `${s}T00:00:00` : s.replace(' ', 'T');
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

type FiltroTema = 'todas' | TemaNoticia;
const FILTROS: { k: FiltroTema; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { k: 'todas', label: 'Todas', icon: 'albums-outline' },
  { k: 'educacion', label: 'Educación', icon: 'school-outline' },
  { k: 'tecnologia', label: 'Tecnología', icon: 'hardware-chip-outline' },
  { k: 'ingenieria_sistemas', label: 'Ingeniería de sistemas', icon: 'code-slash-outline' },
  { k: 'institucional', label: 'UNAB', icon: 'business-outline' },
];
const TEMA_LABEL: Record<TemaNoticia, string> = {
  educacion: 'Educación',
  tecnologia: 'Tecnología',
  ingenieria_sistemas: 'Ingeniería de sistemas',
  institucional: 'UNAB',
};

function host(url?: string | null): string {
  const m = /^https?:\/\/(?:www\.)?([^/]+)/i.exec(url ?? '');
  return m ? m[1].toLowerCase() : '';
}

/** Tema de la noticia; si el backend aún no envía `tema`, se infiere de la URL y del titular. */
function temaDe(n: Noticia): TemaNoticia {
  const t = (n.tema ?? '').toLowerCase();
  if (t === 'educacion' || t === 'tecnologia' || t === 'ingenieria_sistemas' || t === 'institucional') return t;
  if (host(n.url).endsWith('unab.edu.co') || (n.fuente_nombre ?? '').toUpperCase() === 'UNAB') return 'institucional';
  const s = `${n.titulo} ${n.resumen ?? ''}`.toLowerCase();
  if (/ingenier[ií]a de (sistemas|software)|programaci|desarrollador|software|ciberseguridad|ciencia de datos/.test(s)) return 'ingenieria_sistemas';
  if (/educaci|universidad|colegio|docente|estudiante|beca|icetex/.test(s)) return 'educacion';
  return 'tecnologia';
}

/** Medio que publica; sin `fuente_nombre` se usa el dominio de la URL. */
function fuenteDe(n: Noticia): string {
  if (n.fuente_nombre) return n.fuente_nombre;
  const h = host(n.url);
  if (h.endsWith('unab.edu.co')) return 'UNAB';
  if (h === 'news.google.com') return 'Google News';
  return h;
}

/** "Hoy · 10:35", "Ayer · 18:02" o la fecha exacta ("17 nov 2026"). */
function fechaNoticia(d: Date | null): string {
  if (!d) return '';
  const n = diasEntre(d, new Date());
  const hora = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  const conHora = d.getHours() !== 0 || d.getMinutes() !== 0;
  if (n === 0) return conHora ? `Hoy · ${hora}` : 'Hoy';
  if (n === 1) return conHora ? `Ayer · ${hora}` : 'Ayer';
  return fmtFecha(d);
}

function fmtFecha(d: Date | null): string {
  return d ? `${d.getDate()} ${MESES[d.getMonth()].slice(0, 3).toLowerCase()} ${d.getFullYear()}` : '';
}

function diasEntre(a: Date, b: Date): number {
  const A = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime();
  const B = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime();
  return Math.round((B - A) / 86400000);
}

export function NewsScreen({ data, loading, error, refreshing, onRefresh, onRetry }: Props) {
  const { c } = useTheme();
  const [seg, setSeg] = useState<'noticias' | 'calendario'>('noticias');
  const [filtro, setFiltro] = useState<FiltroTema>('todas');

  // Más recientes primero; cada noticia con su tema, medio y fecha ya resueltos
  const todas = useMemo(
    () =>
      (data?.noticias ?? [])
        .map((n) => ({ n, tema: temaDe(n), fuente: fuenteDe(n), fecha: parseFecha(n.fecha_pub) }))
        .sort((a, b) => (b.fecha?.getTime() ?? 0) - (a.fecha?.getTime() ?? 0)),
    [data?.noticias],
  );
  const conteo = useMemo(() => {
    const m: Record<FiltroTema, number> = { todas: todas.length, educacion: 0, tecnologia: 0, ingenieria_sistemas: 0, institucional: 0 };
    for (const x of todas) m[x.tema] += 1;
    return m;
  }, [todas]);
  const noticias = filtro === 'todas' ? todas : todas.filter((x) => x.tema === filtro);
  const hoyN = todas.filter((x) => x.fecha && diasEntre(x.fecha, new Date()) === 0).length;

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
      {seg === 'noticias' && todas.length > 0 ? (
        <View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsBar}>
            {FILTROS.map(({ k, label, icon }) => {
              const on = filtro === k;
              return (
                <Pressable
                  key={k}
                  accessibilityRole="button"
                  accessibilityState={{ selected: on }}
                  onPress={() => {
                    if (!on) haptic('select');
                    setFiltro(k);
                  }}
                  style={({ pressed }) => [
                    styles.chip,
                    {
                      backgroundColor: on ? c.primary : pressed ? alpha(c.primary, 0.2) : c.primarySoft,
                      borderColor: on ? c.primary : alpha(c.primary, 0.35),
                    },
                  ]}
                >
                  <Ionicons name={icon} size={14} color={on ? '#fff' : c.primary} style={{ marginRight: 5 }} />
                  <Txt v="caption" color={on ? '#fff' : c.primary} style={{ fontFamily: fonts.medium }}>
                    {`${label} · ${conteo[k]}`}
                  </Txt>
                </Pressable>
              );
            })}
          </ScrollView>
          {hoyN > 0 ? (
            <Txt v="caption" muted style={{ paddingHorizontal: spacing.lg }}>
              {`${hoyN} ${hoyN === 1 ? 'noticia publicada' : 'noticias publicadas'} hoy`}
            </Txt>
          ) : null}
        </View>
      ) : null}
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
            todas.length > 0 ? (
              <StateView icon="funnel-outline" title="Nada en este tema" message="No hay noticias recientes de este tema. Prueba con otro filtro." onRetry={() => setFiltro('todas')} retryLabel="Ver todas" />
            ) : (
              <StateView icon="newspaper-outline" title="Sin noticias por ahora" message="Cuando haya convocatorias o novedades las verás aquí." onRetry={onRetry} retryLabel="Actualizar" />
            )
          ) : (
            noticias.map(({ n, tema, fuente, fecha }, i) => {
              const col = { educacion: c.blue, tecnologia: c.teal, ingenieria_sistemas: c.primary, institucional: c.orange }[tema];
              const esHoy = !!fecha && diasEntre(fecha, new Date()) === 0;
              const cuando = fechaNoticia(fecha);
              return (
                <FadeIn key={n.url || i} delay={Math.min(i, 6) * 40}>
                  <Pressable onPress={() => n.url && Linking.openURL(n.url).catch(() => undefined)}>
                    <Card>
                      <View style={styles.rowBetween}>
                        <View style={styles.tags}>
                          <View style={{ marginRight: 6 }}>
                            <Badge label={TEMA_LABEL[tema]} color={col} small />
                          </View>
                          {esHoy ? <Badge label="Hoy" color={c.green} solid icon="flash-outline" small /> : null}
                        </View>
                        {n.tipo && n.tipo !== 'general' ? (
                          <Txt v="caption" muted>
                            {n.tipo}
                          </Txt>
                        ) : null}
                      </View>
                      {fuente || cuando ? (
                        <View style={[styles.meta, { marginTop: spacing.sm }]}>
                          <Ionicons name="globe-outline" size={12} color={c.muted} style={{ marginRight: 4 }} />
                          <Txt v="caption" muted numberOfLines={1} style={{ flexShrink: 1 }}>
                            {[fuente, cuando].filter(Boolean).join(' · ')}
                          </Txt>
                        </View>
                      ) : null}
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
  meta: { flexDirection: 'row', alignItems: 'center' },
  chipsBar: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.sm },
  chip: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 7, marginRight: spacing.sm, borderRadius: radius.pill, borderWidth: StyleSheet.hairlineWidth },
});

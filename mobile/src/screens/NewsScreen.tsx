import React, { useState } from 'react';
import { Linking, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { colors } from '../theme';
import type { Dashboard } from '../types';

interface Props {
  data: Dashboard | null;
  refreshing: boolean;
  onRefresh: () => void;
}

function parseFecha(s?: string | null): Date | null {
  if (!s) return null;
  const d = new Date(s.length === 10 ? `${s}T00:00:00` : s);
  return isNaN(d.getTime()) ? null : d;
}

function fmtFecha(s?: string | null): string {
  const d = parseFecha(s);
  if (!d) return '';
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function NewsScreen({ data, refreshing, onRefresh }: Props) {
  const [seg, setSeg] = useState<'noticias' | 'calendario'>('noticias');
  const noticias = data?.noticias ?? [];
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const eventos = (data?.calendario ?? [])
    .filter((e) => {
      const f = parseFecha(e.fecha_fin) ?? parseFecha(e.fecha_inicio);
      return !f || f >= hoy;
    })
    .sort((a, b) => (parseFecha(a.fecha_inicio)?.getTime() ?? 0) - (parseFecha(b.fecha_inicio)?.getTime() ?? 0));

  return (
    <View style={styles.root}>
      <View style={styles.segRow}>
        {(['noticias', 'calendario'] as const).map((k) => (
          <Pressable key={k} style={[styles.seg, seg === k && styles.segOn]} onPress={() => setSeg(k)}>
            <Text style={[styles.segText, seg === k && { color: colors.white }]}>{k === 'noticias' ? 'Noticias' : 'Calendario'}</Text>
          </Pressable>
        ))}
      </View>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[colors.purple]} />}
      >
        {seg === 'noticias' ? (
          noticias.length === 0 ? (
            <Text style={styles.empty}>No hay noticias por ahora.</Text>
          ) : (
            noticias.map((n, i) => (
              <Pressable key={i} onPress={() => n.url && Linking.openURL(n.url).catch(() => undefined)}>
                <Card>
                  {n.tipo ? <Badge label={n.tipo} color={colors.purple} /> : null}
                  <Text style={styles.title}>{n.titulo}</Text>
                  {n.resumen ? (
                    <Text style={styles.resumen} numberOfLines={3}>
                      {n.resumen}
                    </Text>
                  ) : null}
                  {n.fecha_pub ? <Text style={styles.fecha}>{fmtFecha(n.fecha_pub)}</Text> : null}
                </Card>
              </Pressable>
            ))
          )
        ) : eventos.length === 0 ? (
          <Text style={styles.empty}>No hay eventos próximos en el calendario.</Text>
        ) : (
          eventos.map((e, i) => {
            const ini = fmtFecha(e.fecha_inicio);
            const fin = fmtFecha(e.fecha_fin);
            return (
              <Card key={i}>
                {e.categoria ? <Badge label={e.categoria} color={colors.orange} /> : null}
                <Text style={styles.title}>{e.evento}</Text>
                <Text style={styles.fecha}>{ini && fin && ini !== fin ? `${ini} – ${fin}` : ini || fin}</Text>
              </Card>
            );
          })
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  segRow: {
    flexDirection: 'row',
    margin: 16,
    marginBottom: 0,
    backgroundColor: '#E8EAF2',
    borderRadius: 12,
    padding: 3,
  },
  seg: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 10 },
  segOn: { backgroundColor: colors.purple },
  segText: { fontWeight: '700', color: colors.navy },
  content: { padding: 16, paddingBottom: 32 },
  empty: { color: colors.muted, textAlign: 'center', marginTop: 40 },
  title: { fontSize: 15, fontWeight: '700', color: colors.navy, marginTop: 6 },
  resumen: { color: colors.muted, fontSize: 13, marginTop: 4 },
  fecha: { color: colors.muted, fontSize: 12, marginTop: 6 },
});

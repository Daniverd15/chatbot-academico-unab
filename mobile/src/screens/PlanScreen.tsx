import React, { useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, estadoCursoColor } from '../theme';
import type { Dashboard } from '../types';

interface Props {
  data: Dashboard | null;
  refreshing: boolean;
  onRefresh: () => void;
}

export function PlanScreen({ data, refreshing, onRefresh }: Props) {
  const [open, setOpen] = useState<Record<number, boolean>>({});
  const avance = [...(data?.avance ?? [])].sort((a, b) => a.semestre - b.semestre);

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[colors.purple]} />}
    >
      <View style={styles.legend}>
        {Object.entries(estadoCursoColor).map(([k, c]) => (
          <View key={k} style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: c }]} />
            <Text style={styles.legendText}>{k}</Text>
          </View>
        ))}
      </View>
      {avance.length === 0 ? <Text style={styles.empty}>Aún no hay información de tu plan de estudios.</Text> : null}
      {avance.map((s) => {
        const cursos = s.cursos ?? [];
        const total = cursos.reduce((a, c) => a + (c.creditos ?? 0), 0);
        const aprob = cursos.filter((c) => c.estado === 'Aprobado').reduce((a, c) => a + (c.creditos ?? 0), 0);
        const isOpen = !!open[s.semestre];
        return (
          <View key={s.semestre} style={styles.section}>
            <Pressable style={styles.header} onPress={() => setOpen((o) => ({ ...o, [s.semestre]: !o[s.semestre] }))}>
              <View style={{ flex: 1 }}>
                <Text style={styles.semTitle}>Semestre {s.semestre}</Text>
                <Text style={styles.semSub}>
                  {aprob} / {total} créditos aprobados
                </Text>
              </View>
              <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={20} color={colors.muted} />
            </Pressable>
            {isOpen
              ? cursos.map((c, i) => (
                  <View key={`${c.curso_id}-${i}`} style={styles.course}>
                    <View style={[styles.dot, { backgroundColor: estadoCursoColor[c.estado] ?? colors.gray }]} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.courseName}>{c.curso}</Text>
                      <Text style={styles.semSub}>
                        {c.creditos} créditos · {c.estado}
                      </Text>
                    </View>
                    <Text style={styles.grade}>{typeof c.nota_aprobacion === 'number' ? c.nota_aprobacion.toFixed(1) : '—'}</Text>
                  </View>
                ))
              : null}
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginRight: 12, marginBottom: 4 },
  legendText: { fontSize: 12, color: colors.muted },
  empty: { color: colors.muted, textAlign: 'center', marginTop: 40 },
  section: {
    backgroundColor: colors.white,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 10,
    overflow: 'hidden',
  },
  header: { flexDirection: 'row', alignItems: 'center', padding: 14 },
  semTitle: { fontSize: 16, fontWeight: '700', color: colors.navy },
  semSub: { fontSize: 12, color: colors.muted, marginTop: 2 },
  course: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  courseName: { fontSize: 14, color: colors.navy, fontWeight: '600' },
  grade: { fontSize: 15, fontWeight: '700', color: colors.navy, marginLeft: 8 },
});

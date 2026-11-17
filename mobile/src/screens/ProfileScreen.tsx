import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Card } from '../components/Card';
import { colors, radius } from '../theme';
import type { Resumen, Sesion } from '../types';

interface Props {
  sesion: Sesion;
  resumen: Resumen | null;
  onLogout: () => void;
}

export function ProfileScreen({ sesion, resumen, onLogout }: Props) {
  const confirmar = () =>
    Alert.alert('Cerrar sesión', '¿Seguro que quieres cerrar sesión?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Cerrar sesión', style: 'destructive', onPress: onLogout },
    ]);

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.bg }} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <Text style={styles.name}>{resumen?.nombre_completo || sesion.nombre}</Text>
        <Row label="Código" value={sesion.codigo} />
        <Row label="Correo" value={resumen?.email} />
        <Row label="Programa" value={resumen?.programa} />
        <Row label="Cohorte" value={resumen?.cohorte != null ? String(resumen.cohorte) : undefined} />
      </Card>
      <Pressable style={styles.logout} onPress={confirmar}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </Pressable>
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value || '—'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  name: { fontSize: 20, fontWeight: '800', color: colors.navy, marginBottom: 10 },
  row: { paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border },
  label: { fontSize: 12, color: colors.muted },
  value: { fontSize: 15, color: colors.navy, fontWeight: '600', marginTop: 2 },
  logout: { backgroundColor: colors.red, borderRadius: radius.md, paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  logoutText: { color: colors.white, fontWeight: '700', fontSize: 16 },
});

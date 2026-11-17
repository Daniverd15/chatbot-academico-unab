import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Card } from '../components/Card';
import { PressableScale } from '../components/PressableScale';
import { Txt } from '../components/Txt';
import { haptic } from '../haptics';
import { alpha, radius, spacing, ThemeMode, useTheme } from '../theme';
import type { Resumen, Sesion } from '../types';

interface Props {
  sesion: Sesion;
  resumen: Resumen | null;
  onLogout: () => void;
}

const MODOS: { key: ThemeMode; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'system', label: 'Sistema', icon: 'phone-portrait-outline' },
  { key: 'light', label: 'Claro', icon: 'sunny-outline' },
  { key: 'dark', label: 'Oscuro', icon: 'moon-outline' },
];

export function ProfileScreen({ sesion, resumen, onLogout }: Props) {
  const { c, mode, setMode } = useTheme();
  const nombre = resumen?.nombre_completo || sesion.nombre;
  const iniciales = (nombre || '?')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join('');

  const confirmar = () =>
    Alert.alert('Cerrar sesión', '¿Seguro que quieres cerrar sesión?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Cerrar sesión', style: 'destructive', onPress: onLogout },
    ]);

  return (
    <ScrollView style={{ flex: 1, backgroundColor: c.bg }} contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxl }} showsVerticalScrollIndicator={false}>
      <View style={styles.top}>
        <LinearGradient colors={c.gradient} style={styles.avatar}>
          <Txt v="title" color="#fff">
            {iniciales}
          </Txt>
        </LinearGradient>
        <Txt v="h2" style={{ marginTop: spacing.md, textAlign: 'center' }}>
          {nombre}
        </Txt>
        <Txt v="small" muted>
          {sesion.codigo}
        </Txt>
      </View>

      <Card title="Mis datos" icon="person-outline">
        <Row icon="mail-outline" label="Correo" value={resumen?.email} />
        <Row icon="school-outline" label="Programa" value={resumen?.programa} />
        <Row icon="calendar-outline" label="Cohorte" value={resumen?.cohorte != null ? String(resumen.cohorte) : undefined} last />
      </Card>

      <Card title="Apariencia" icon="color-palette-outline">
        <View style={[styles.seg, { backgroundColor: c.cardAlt }]}>
          {MODOS.map((m) => {
            const on = mode === m.key;
            return (
              <Pressable
                key={m.key}
                style={[styles.segItem, on && { backgroundColor: c.primary }]}
                onPress={() => {
                  haptic('select');
                  setMode(m.key);
                }}
                accessibilityRole="button"
                accessibilityState={{ selected: on }}
              >
                <Ionicons name={m.icon} size={16} color={on ? '#fff' : c.muted} />
                <Txt v="label" color={on ? '#fff' : c.muted} style={{ marginLeft: 6 }}>
                  {m.label}
                </Txt>
              </Pressable>
            );
          })}
        </View>
        <Txt v="caption" muted style={{ marginTop: spacing.sm }}>
          {mode === 'system' ? 'La app sigue el tema de tu dispositivo.' : mode === 'dark' ? 'Modo oscuro activado.' : 'Modo claro activado.'}
        </Txt>
      </Card>

      <PressableScale onPress={confirmar} style={[styles.logout, { backgroundColor: alpha(c.red, 0.12), borderColor: alpha(c.red, 0.45) }]}>
        <Ionicons name="log-out-outline" size={20} color={c.red} />
        <Txt v="button" color={c.red} style={{ marginLeft: spacing.sm }}>
          Cerrar sesión
        </Txt>
      </PressableScale>
    </ScrollView>
  );
}

function Row({ icon, label, value, last }: { icon: keyof typeof Ionicons.glyphMap; label: string; value?: string; last?: boolean }) {
  const { c } = useTheme();
  return (
    <View style={[styles.row, !last && { borderBottomColor: c.border, borderBottomWidth: StyleSheet.hairlineWidth }]}>
      <Ionicons name={icon} size={18} color={c.primary} />
      <View style={{ flex: 1, marginLeft: spacing.md }}>
        <Txt v="caption" muted>
          {label}
        </Txt>
        <Txt v="bodyMedium">{value || '—'}</Txt>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  top: { alignItems: 'center', marginVertical: spacing.lg },
  avatar: { width: 84, height: 84, borderRadius: 42, alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.md },
  seg: { flexDirection: 'row', borderRadius: radius.md, padding: 4 },
  segItem: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 9, borderRadius: radius.md - 4 },
  logout: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', borderRadius: radius.md, borderWidth: 1, paddingVertical: 14 },
});

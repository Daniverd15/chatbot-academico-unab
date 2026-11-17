import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme';

export type TabKey = 'inicio' | 'chat' | 'plan' | 'novedades';

const TABS: { key: TabKey; label: string; icon: keyof typeof Ionicons.glyphMap; iconOff: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'inicio', label: 'Inicio', icon: 'home', iconOff: 'home-outline' },
  { key: 'chat', label: 'Chat', icon: 'chatbubbles', iconOff: 'chatbubbles-outline' },
  { key: 'plan', label: 'Plan', icon: 'school', iconOff: 'school-outline' },
  { key: 'novedades', label: 'Novedades', icon: 'newspaper', iconOff: 'newspaper-outline' },
];

export function TabBar({ active, onChange }: { active: TabKey; onChange: (k: TabKey) => void }) {
  return (
    <View style={styles.bar}>
      {TABS.map((t) => {
        const on = t.key === active;
        return (
          <Pressable key={t.key} style={styles.tab} onPress={() => onChange(t.key)}>
            <Ionicons name={on ? t.icon : t.iconOff} size={22} color={on ? colors.purple : colors.muted} />
            <Text style={[styles.label, { color: on ? colors.purple : colors.muted }]}>{t.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingBottom: 6,
    paddingTop: 6,
  },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 4 },
  label: { fontSize: 11, marginTop: 2, fontWeight: '600' },
});

import React, { useEffect, useRef } from 'react';
import { Animated, Pressable, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { alpha, shadow, useTheme } from '../theme';
import { haptic } from '../haptics';
import { Txt } from './Txt';

export type TabKey = 'inicio' | 'chat' | 'plan' | 'novedades';

const TABS: { key: TabKey; label: string; icon: keyof typeof Ionicons.glyphMap; iconOff: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'inicio', label: 'Inicio', icon: 'home', iconOff: 'home-outline' },
  { key: 'chat', label: 'Chat', icon: 'chatbubbles', iconOff: 'chatbubbles-outline' },
  { key: 'plan', label: 'Plan', icon: 'school', iconOff: 'school-outline' },
  { key: 'novedades', label: 'Novedades', icon: 'newspaper', iconOff: 'newspaper-outline' },
];

function Item({ t, on, onPress }: { t: (typeof TABS)[number]; on: boolean; onPress: () => void }) {
  const { c } = useTheme();
  const v = useRef(new Animated.Value(on ? 1 : 0)).current;
  useEffect(() => {
    Animated.spring(v, { toValue: on ? 1 : 0, useNativeDriver: true, speed: 20, bounciness: 8 }).start();
  }, [on, v]);
  const scale = v.interpolate({ inputRange: [0, 1], outputRange: [1, 1.12] });
  return (
    <Pressable style={styles.tab} onPress={onPress} accessibilityRole="tab" accessibilityState={{ selected: on }}>
      <View style={[styles.pill, { backgroundColor: on ? alpha(c.primary, 0.14) : 'transparent' }]}>
        <Animated.View style={{ transform: [{ scale }] }}>
          <Ionicons name={on ? t.icon : t.iconOff} size={22} color={on ? c.primary : c.muted} />
        </Animated.View>
      </View>
      <Txt v="caption" color={on ? c.primary : c.muted} style={{ fontFamily: on ? 'Poppins_600SemiBold' : 'Poppins_400Regular', fontSize: 11 }}>
        {t.label}
      </Txt>
    </Pressable>
  );
}

export function TabBar({ active, onChange }: { active: TabKey; onChange: (k: TabKey) => void }) {
  const { c } = useTheme();
  return (
    <View style={[styles.bar, shadow(3, c), { backgroundColor: c.tabBar, borderTopColor: c.border }]}>
      {TABS.map((t) => (
        <Item
          key={t.key}
          t={t}
          on={t.key === active}
          onPress={() => {
            if (t.key !== active) haptic('select');
            onChange(t.key);
          }}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { flexDirection: 'row', borderTopWidth: StyleSheet.hairlineWidth, paddingBottom: 8, paddingTop: 6 },
  tab: { flex: 1, alignItems: 'center' },
  pill: { paddingHorizontal: 18, paddingVertical: 4, borderRadius: 16, marginBottom: 1 },
});

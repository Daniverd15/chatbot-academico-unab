import React, { useRef, useState } from 'react';
import { ActivityIndicator, Animated, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { alpha, brand, fonts, radius, shadow, spacing, topInset, typography, useTheme } from '../theme';
import { ApiError, login } from '../api';
import { haptic } from '../haptics';
import { Logo } from '../components/Logo';
import { PressableScale } from '../components/PressableScale';
import { Txt } from '../components/Txt';
import { Transition } from '../components/Transition';
import type { Sesion } from '../types';

const CODIGO_RE = /^U\d{8}$/;

export function LoginScreen({ onLogin }: { onLogin: (s: Sesion) => void }) {
  const { c } = useTheme();
  const [codigo, setCodigo] = useState('');
  const [pin, setPin] = useState('');
  const [verPin, setVerPin] = useState(false);
  const [focus, setFocus] = useState<'codigo' | 'pin' | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ campo?: 'codigo' | 'pin'; msg: string } | null>(null);
  const shake = useRef(new Animated.Value(0)).current;
  const pinRef = useRef<React.ComponentRef<typeof TextInput>>(null);

  const fail = (msg: string, campo?: 'codigo' | 'pin') => {
    setError({ msg, campo });
    haptic('warning');
    shake.setValue(0);
    Animated.sequence([
      Animated.timing(shake, { toValue: 1, duration: 60, useNativeDriver: true }),
      Animated.timing(shake, { toValue: -1, duration: 90, useNativeDriver: true }),
      Animated.timing(shake, { toValue: 1, duration: 90, useNativeDriver: true }),
      Animated.timing(shake, { toValue: 0, duration: 60, useNativeDriver: true }),
    ]).start();
  };

  const submit = async () => {
    if (loading) return;
    const cod = codigo.trim().toUpperCase();
    if (!CODIGO_RE.test(cod)) return fail('El código estudiantil debe tener el formato U######## (la U y 8 números).', 'codigo');
    if (!/^\d{4,8}$/.test(pin)) return fail('El PIN debe tener entre 4 y 8 números.', 'pin');
    setError(null);
    setLoading(true);
    try {
      const r = await login({ codigo: cod, pin });
      if (r.ok && r.estudiante) {
        haptic('success');
        onLogin({ codigo: cod, pin, nombre: r.estudiante.nombre_completo });
      } else {
        fail(r.mensaje || 'Código o PIN incorrectos. Verifica e intenta de nuevo.');
      }
    } catch (e) {
      fail(e instanceof ApiError ? e.message : 'Ocurrió un error inesperado. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const borde = (campo: 'codigo' | 'pin') =>
    error?.campo === campo ? c.red : focus === campo ? c.primary : 'transparent';

  const inputStyle = [styles.input, { color: c.text, fontFamily: fonts.medium }];

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.bg }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <LinearGradient colors={[brand.purple, brand.navy]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.hero}>
          <View style={[styles.blob, { top: -40, right: -50, width: 190, height: 190, backgroundColor: 'rgba(247,166,0,0.18)' }]} />
          <View style={[styles.blob, { bottom: 10, left: -60, width: 150, height: 150, backgroundColor: 'rgba(255,255,255,0.07)' }]} />
          <Transition dy={-10} style={{ flex: 0, alignItems: 'center' }}>
            <Logo size={84} />
            <Txt v="display" color="#fff" style={{ marginTop: spacing.md, letterSpacing: 1 }}>
              UNABot
            </Txt>
            <Txt v="small" color={brand.orange} style={{ fontFamily: fonts.medium, marginTop: 2 }}>
              Tu asistente académico UNAB
            </Txt>
          </Transition>
        </LinearGradient>

        <Transition style={{ flex: 1, paddingHorizontal: spacing.lg }}>
          <Animated.View
            style={[
              styles.card,
              shadow(3, c),
              { backgroundColor: c.card, transform: [{ translateX: shake.interpolate({ inputRange: [-1, 1], outputRange: [-8, 8] }) }] },
            ]}
          >
            <Txt v="title">Inicia sesión</Txt>
            <Txt v="small" muted style={{ marginBottom: spacing.sm }}>
              Usa tu código estudiantil y tu PIN.
            </Txt>

            <Txt v="label" muted style={styles.label}>
              Código estudiantil
            </Txt>
            <View style={[styles.field, { backgroundColor: c.inputBg, borderColor: borde('codigo') }]}>
              <Ionicons name="person-outline" size={18} color={focus === 'codigo' ? c.primary : c.muted} />
              <TextInput
                style={inputStyle}
                value={codigo}
                onChangeText={(t) => {
                  setCodigo(t.toUpperCase());
                  if (error) setError(null);
                }}
                placeholder="U00100001"
                placeholderTextColor={c.gray}
                autoCapitalize="characters"
                autoCorrect={false}
                maxLength={9}
                returnKeyType="next"
                onFocus={() => setFocus('codigo')}
                onBlur={() => setFocus(null)}
                onSubmitEditing={() => pinRef.current?.focus()}
              />
            </View>

            <Txt v="label" muted style={styles.label}>
              PIN
            </Txt>
            <View style={[styles.field, { backgroundColor: c.inputBg, borderColor: borde('pin') }]}>
              <Ionicons name="lock-closed-outline" size={18} color={focus === 'pin' ? c.primary : c.muted} />
              <TextInput
                ref={pinRef}
                style={inputStyle}
                value={pin}
                onChangeText={(t) => {
                  setPin(t.replace(/\D/g, ''));
                  if (error) setError(null);
                }}
                placeholder="••••"
                placeholderTextColor={c.gray}
                secureTextEntry={!verPin}
                keyboardType="number-pad"
                maxLength={8}
                onFocus={() => setFocus('pin')}
                onBlur={() => setFocus(null)}
                onSubmitEditing={submit}
              />
              <Pressable onPress={() => setVerPin((v) => !v)} hitSlop={10} accessibilityLabel={verPin ? 'Ocultar PIN' : 'Mostrar PIN'}>
                <Ionicons name={verPin ? 'eye-off-outline' : 'eye-outline'} size={20} color={c.muted} />
              </Pressable>
            </View>

            {error ? (
              <View style={[styles.error, { backgroundColor: alpha(c.red, 0.12), borderColor: alpha(c.red, 0.4) }]}>
                <Ionicons name="alert-circle" size={18} color={c.red} style={{ marginTop: 1 }} />
                <Txt v="small" color={c.red} style={{ flex: 1, marginLeft: spacing.sm }}>
                  {error.msg}
                </Txt>
              </View>
            ) : null}

            <PressableScale onPress={submit} disabled={loading} style={[styles.buttonWrap, shadow(2, c), loading && { opacity: 0.85 }]}>
              <LinearGradient colors={[brand.purple, '#6A00B0']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.button}>
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Txt v="button" color="#fff">
                      Ingresar
                    </Txt>
                    <Ionicons name="arrow-forward" size={18} color="#fff" style={{ marginLeft: 8 }} />
                  </>
                )}
              </LinearGradient>
            </PressableScale>

            <View style={[styles.hint, { backgroundColor: c.primarySoft }]}>
              <Ionicons name="information-circle-outline" size={16} color={c.primary} />
              <Txt v="caption" color={c.primary} style={{ marginLeft: 6 }}>
                Demo: U00100001 · PIN 1234
              </Txt>
            </View>
          </Animated.View>
        </Transition>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  hero: {
    alignItems: 'center',
    paddingTop: topInset + 36,
    paddingBottom: 90,
    borderBottomLeftRadius: radius.xl,
    borderBottomRightRadius: radius.xl,
    overflow: 'hidden',
  },
  blob: { position: 'absolute', borderRadius: 999 },
  card: {
    marginTop: -56,
    borderRadius: radius.xl,
    padding: spacing.xl,
    marginBottom: spacing.xl,
  },
  label: { marginTop: spacing.md, marginBottom: 6 },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1.5,
    paddingHorizontal: spacing.md,
  },
  input: { flex: 1, ...typography.body, paddingVertical: 12, paddingHorizontal: spacing.sm },
  error: { flexDirection: 'row', borderRadius: radius.md, borderWidth: 1, padding: spacing.md, marginTop: spacing.lg },
  buttonWrap: { marginTop: spacing.xl, borderRadius: radius.md },
  button: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, borderRadius: radius.md },
  hint: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', borderRadius: radius.pill, paddingVertical: 8, marginTop: spacing.lg },
});

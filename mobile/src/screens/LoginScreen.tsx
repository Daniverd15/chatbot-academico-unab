import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius, topInset } from '../theme';
import { ApiError, login } from '../api';
import type { Sesion } from '../types';

const CODIGO_RE = /^U\d{8}$/;

export function LoginScreen({ onLogin }: { onLogin: (s: Sesion) => void }) {
  const [codigo, setCodigo] = useState('');
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const c = codigo.trim().toUpperCase();
    if (!CODIGO_RE.test(c)) {
      setError('El código estudiantil debe tener el formato U######## (la U y 8 números).');
      return;
    }
    if (!/^\d{4,8}$/.test(pin)) {
      setError('El PIN debe tener entre 4 y 8 números.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const r = await login({ codigo: c, pin });
      if (r.ok && r.estudiante) {
        onLogin({ codigo: c, pin, nombre: r.estudiante.nombre_completo });
      } else {
        setError(r.mensaje || 'Código o PIN incorrectos. Verifica e intenta de nuevo.');
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Ocurrió un error inesperado. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <View style={styles.logo}>
            <Ionicons name="school" size={40} color={colors.white} />
          </View>
          <Text style={styles.brand}>UNAB</Text>
          <Text style={styles.subtitle}>Asistente académico · Ingeniería de Sistemas</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.title}>Inicia sesión</Text>
          <Text style={styles.label}>Código estudiantil</Text>
          <TextInput
            style={styles.input}
            value={codigo}
            onChangeText={(t) => setCodigo(t.toUpperCase())}
            placeholder="U00100001"
            placeholderTextColor={colors.gray}
            autoCapitalize="characters"
            autoCorrect={false}
            maxLength={9}
          />
          <Text style={styles.label}>PIN</Text>
          <TextInput
            style={styles.input}
            value={pin}
            onChangeText={(t) => setPin(t.replace(/\D/g, ''))}
            placeholder="••••"
            placeholderTextColor={colors.gray}
            secureTextEntry
            keyboardType="number-pad"
            maxLength={8}
            onSubmitEditing={submit}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable style={[styles.button, loading && { opacity: 0.7 }]} onPress={submit} disabled={loading}>
            {loading ? <ActivityIndicator color={colors.white} /> : <Text style={styles.buttonText}>Ingresar</Text>}
          </Pressable>
          <Text style={styles.hint}>Demo: U00100001 · PIN 1234</Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.navy },
  scroll: { flexGrow: 1 },
  hero: { alignItems: 'center', paddingTop: topInset + 40, paddingBottom: 32 },
  logo: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: colors.purple,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.orange,
  },
  brand: { color: colors.white, fontSize: 34, fontWeight: '800', marginTop: 12, letterSpacing: 4 },
  subtitle: { color: colors.orange, fontSize: 13, marginTop: 4, fontWeight: '600' },
  form: {
    flex: 1,
    backgroundColor: colors.white,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
  },
  title: { fontSize: 22, fontWeight: '800', color: colors.navy, marginBottom: 16 },
  label: { fontSize: 13, fontWeight: '600', color: colors.muted, marginBottom: 6, marginTop: 8 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.navy,
    backgroundColor: colors.bg,
  },
  error: { color: colors.red, marginTop: 12, fontSize: 14 },
  button: {
    backgroundColor: colors.purple,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 20,
  },
  buttonText: { color: colors.white, fontSize: 16, fontWeight: '700' },
  hint: { textAlign: 'center', color: colors.muted, marginTop: 18, fontSize: 13 },
});

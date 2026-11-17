import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, BackHandler, Pressable, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import {
  Poppins_400Regular,
  Poppins_500Medium,
  Poppins_600SemiBold,
  Poppins_700Bold,
  useFonts,
} from '@expo-google-fonts/poppins';
import { ApiError, getDashboard, login } from './src/api';
import { borrarSesion, guardarSesion, leerSesion } from './src/storage';
import { brand, spacing, ThemeProvider, topInset, useTheme } from './src/theme';
import { TabBar, TabKey } from './src/components/TabBar';
import { Transition } from './src/components/Transition';
import { Logo } from './src/components/Logo';
import { Txt } from './src/components/Txt';
import { LoginScreen } from './src/screens/LoginScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { ChatScreen } from './src/screens/ChatScreen';
import { PlanScreen } from './src/screens/PlanScreen';
import { NewsScreen } from './src/screens/NewsScreen';
import { ProfileScreen } from './src/screens/ProfileScreen';
import type { ChatMessage, Dashboard, Sesion } from './src/types';

const TITULOS: Record<TabKey, string> = {
  inicio: 'Inicio',
  chat: 'Asistente UNAB',
  plan: 'Plan de estudios',
  novedades: 'Novedades',
};

export default function App() {
  return (
    <ThemeProvider>
      <Root />
    </ThemeProvider>
  );
}

function Splash() {
  return (
    <LinearGradient colors={[brand.purple, brand.navy]} style={styles.center}>
      <Logo size={88} />
      <Txt v="title" color="#fff" style={{ marginTop: spacing.md }}>
        UNABot
      </Txt>
      <ActivityIndicator color={brand.orange} style={{ marginTop: spacing.lg }} />
      <StatusBar style="light" />
    </LinearGradient>
  );
}

function Root() {
  const { c, ready } = useTheme();
  const [fontsLoaded, fontError] = useFonts({ Poppins_400Regular, Poppins_500Medium, Poppins_600SemiBold, Poppins_700Bold });
  const [booting, setBooting] = useState(true);
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [tab, setTab] = useState<TabKey>('inicio');
  const [perfil, setPerfil] = useState(false);
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const cargar = useCallback(async (s: Sesion, pull = false) => {
    if (pull) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const d = await getDashboard({ codigo: s.codigo, pin: s.pin });
      if (d.ok) setData(d);
      else setError(d.mensaje || 'No pudimos cargar tu información.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Ocurrió un error inesperado.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Auto-login
  useEffect(() => {
    (async () => {
      const s = await leerSesion();
      if (s) {
        try {
          const r = await login({ codigo: s.codigo, pin: s.pin });
          if (r.ok) {
            const ses = { ...s, nombre: r.estudiante?.nombre_completo ?? s.nombre };
            setSesion(ses);
            cargar(ses);
          } else {
            await borrarSesion();
          }
        } catch {
          // Sin conexión: entrar con la sesión guardada
          setSesion(s);
          cargar(s);
        }
      }
      setBooting(false);
    })();
  }, [cargar]);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (perfil) {
        setPerfil(false);
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [perfil]);

  const onLogin = async (s: Sesion) => {
    await guardarSesion(s);
    setSesion(s);
    setTab('inicio');
    cargar(s);
  };

  const onLogout = async () => {
    await borrarSesion();
    setSesion(null);
    setData(null);
    setMessages([]);
    setPerfil(false);
    setError(null);
  };

  if ((!fontsLoaded && !fontError) || !ready || booting) return <Splash />;

  if (!sesion) {
    return (
      <>
        <LoginScreen onLogin={onLogin} />
        <StatusBar style="light" />
      </>
    );
  }

  const refresh = () => cargar(sesion, true);
  const retry = () => cargar(sesion);

  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <StatusBar style="light" />
      <LinearGradient colors={c.gradient} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.header}>
        {perfil ? (
          <Pressable onPress={() => setPerfil(false)} hitSlop={12} style={styles.hBtn} accessibilityLabel="Volver">
            <Ionicons name="arrow-back" size={22} color="#fff" />
          </Pressable>
        ) : (
          <View style={{ marginRight: spacing.md }}>
            <Logo size={32} />
          </View>
        )}
        <Txt v="h2" color="#fff" style={{ flex: 1 }}>
          {perfil ? 'Mi perfil' : TITULOS[tab]}
        </Txt>
        {!perfil ? (
          <Pressable onPress={() => setPerfil(true)} hitSlop={12} style={styles.hBtn} accessibilityLabel="Mi perfil">
            <Ionicons name="person-outline" size={20} color="#fff" />
          </Pressable>
        ) : null}
        <View style={styles.accent} />
      </LinearGradient>

      <View style={{ flex: 1 }}>
        <Transition key={perfil ? 'perfil' : tab}>
          {perfil ? (
            <ProfileScreen sesion={sesion} resumen={data?.resumen ?? null} onLogout={onLogout} />
          ) : tab === 'inicio' ? (
            <HomeScreen
              nombre={data?.resumen?.nombre_completo || sesion.nombre}
              data={data}
              loading={loading}
              error={error}
              refreshing={refreshing}
              onRefresh={refresh}
              onRetry={retry}
            />
          ) : tab === 'chat' ? (
            <ChatScreen cred={{ codigo: sesion.codigo, pin: sesion.pin }} messages={messages} setMessages={setMessages} />
          ) : tab === 'plan' ? (
            <PlanScreen data={data} loading={loading} error={error} refreshing={refreshing} onRefresh={refresh} onRetry={retry} />
          ) : (
            <NewsScreen data={data} loading={loading} error={error} refreshing={refreshing} onRefresh={refresh} onRetry={retry} />
          )}
        </Transition>
      </View>
      {!perfil ? <TabBar active={tab} onChange={setTab} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    paddingTop: topInset + 8,
    paddingBottom: 14,
    paddingHorizontal: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
  },
  hBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.16)',
    marginRight: spacing.sm,
  },
  accent: { position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, backgroundColor: brand.orange },
});

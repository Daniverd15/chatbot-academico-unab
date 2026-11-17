import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, BackHandler, Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { ApiError, getDashboard, login } from './src/api';
import { borrarSesion, guardarSesion, leerSesion } from './src/storage';
import { colors, topInset } from './src/theme';
import { TabBar, TabKey } from './src/components/TabBar';
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

  if (booting) {
    return (
      <View style={[styles.center, { backgroundColor: colors.navy }]}>
        <ActivityIndicator size="large" color={colors.orange} />
        <StatusBar style="light" />
      </View>
    );
  }

  if (!sesion) {
    return (
      <>
        <LoginScreen onLogin={onLogin} />
        <StatusBar style="light" />
      </>
    );
  }

  const refresh = () => cargar(sesion, true);

  return (
    <View style={styles.root}>
      <StatusBar style="light" />
      <View style={styles.header}>
        {perfil ? (
          <Pressable onPress={() => setPerfil(false)} hitSlop={10}>
            <Ionicons name="arrow-back" size={24} color={colors.white} />
          </Pressable>
        ) : null}
        <Text style={styles.headerTitle}>{perfil ? 'Mi perfil' : TITULOS[tab]}</Text>
        {!perfil ? (
          <Pressable onPress={() => setPerfil(true)} hitSlop={10}>
            <Ionicons name="person-circle-outline" size={28} color={colors.white} />
          </Pressable>
        ) : null}
      </View>
      <View style={{ flex: 1 }}>
        {perfil ? (
          <ProfileScreen sesion={sesion} resumen={data?.resumen ?? null} onLogout={onLogout} />
        ) : tab === 'inicio' ? (
          <HomeScreen nombre={data?.resumen?.nombre_completo || sesion.nombre} data={data} loading={loading} error={error} refreshing={refreshing} onRefresh={refresh} />
        ) : tab === 'chat' ? (
          <ChatScreen cred={{ codigo: sesion.codigo, pin: sesion.pin }} messages={messages} setMessages={setMessages} />
        ) : tab === 'plan' ? (
          <PlanScreen data={data} refreshing={refreshing} onRefresh={refresh} />
        ) : (
          <NewsScreen data={data} refreshing={refreshing} onRefresh={refresh} />
        )}
      </View>
      {!perfil ? <TabBar active={tab} onChange={setTab} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    backgroundColor: colors.navy,
    paddingTop: topInset + 8,
    paddingBottom: 12,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 3,
    borderBottomColor: colors.orange,
  },
  headerTitle: { flex: 1, color: colors.white, fontSize: 18, fontWeight: '700', marginLeft: 0 },
});

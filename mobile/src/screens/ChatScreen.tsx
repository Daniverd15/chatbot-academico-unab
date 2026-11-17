import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  FlatList,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Speech from 'expo-speech';
import { Markdown, stripMarkdown } from '../components/Markdown';
import { Logo } from '../components/Logo';
import { Badge } from '../components/Badge';
import { TypingDots } from '../components/TypingDots';
import { Txt } from '../components/Txt';
import { PressableScale } from '../components/PressableScale';
import { ApiError, sendChat, sendFeedback } from '../api';
import { haptic } from '../haptics';
import { alpha, brand, fonts, radius, shadow, spacing, typography, useTheme } from '../theme';
import type { Palette } from '../theme';
import type { ChatMessage, Credenciales } from '../types';

const SUGERENCIAS = [
  '¿Cómo voy en la carrera?',
  '¿Cuándo me gradúo?',
  '¿Qué cursos puedo inscribir?',
  '¿Qué es la insignia de competencias digitales?',
  '¿Cuándo son las inscripciones de competencias digitales?',
  '¿Qué cursos de competencias digitales he tomado?',
  'Noticias y convocatorias nuevas',
];

interface Props {
  cred: Credenciales;
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

function hhmm(ts: number): string {
  const d = new Date(ts);
  const h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, '0');
  return `${h % 12 === 0 ? 12 : h % 12}:${m} ${h < 12 ? 'a. m.' : 'p. m.'}`;
}

function intentInfo(c: Palette, intencion?: string, bloqueado?: boolean): { label: string; color: string; icon: keyof typeof Ionicons.glyphMap } | null {
  const i = (intencion ?? '').toLowerCase();
  if (bloqueado || i.includes('bloque')) return { label: 'Bloqueado', color: c.red, icon: 'shield-checkmark' };
  if (!i) return null;
  if (i.includes('calend')) return { label: 'Calendario', color: c.orange, icon: 'calendar' };
  if (i.includes('noticia')) return { label: 'Noticias', color: c.blue, icon: 'newspaper' };
  if (i.includes('histor')) return { label: 'Historial', color: c.teal, icon: 'time' };
  if (i.includes('rag') || i.includes('institu') || i.includes('document')) return { label: 'RAG institucional', color: c.primary, icon: 'library' };
  if (i.includes('asesor') || i.includes('academ') || i.includes('avance') || i.includes('plan')) return { label: 'Asesoría académica', color: c.green, icon: 'school' };
  const t = i.replace(/_/g, ' ');
  return { label: t.charAt(0).toUpperCase() + t.slice(1), color: c.gray, icon: 'chatbubble-ellipses' };
}

export function ChatScreen({ cred, messages, setMessages }: Props) {
  const { c } = useTheme();
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const listRef = useRef<FlatList<ChatMessage>>(null);

  useEffect(() => () => void Speech.stop(), []);

  const scrollEnd = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
  }, []);

  const send = useCallback(
    async (texto: string) => {
      const t = texto.trim();
      if (!t || sending) return;
      setInput('');
      haptic('light');
      setMessages((m) => [...m, { id: `u${Date.now()}`, role: 'user', text: t, ts: Date.now() }]);
      setSending(true);
      scrollEnd();
      try {
        const r = await sendChat(cred, t);
        setMessages((m) => [
          ...m,
          {
            id: `b${Date.now()}`,
            role: 'bot',
            ts: Date.now(),
            text: r?.respuesta || 'No pude generar una respuesta. Intenta reformular tu pregunta.',
            fuentes: Array.isArray(r?.fuentes) ? r.fuentes : undefined,
            bloqueado: r?.bloqueado,
            intencion: r?.intencion,
            logId: typeof r?.log_id === 'number' ? r.log_id : null,
          },
        ]);
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : 'Ocurrió un error inesperado. Intenta de nuevo.';
        setMessages((m) => [...m, { id: `e${Date.now()}`, role: 'bot', text: msg, ts: Date.now(), esError: true }]);
      } finally {
        setSending(false);
        scrollEnd();
      }
    },
    [cred, sending, setMessages, scrollEnd],
  );

  const vote = useCallback(
    async (msg: ChatMessage, voto: 'up' | 'down') => {
      if (msg.voto || typeof msg.logId !== 'number') return;
      haptic('success');
      const patch = (p: Partial<ChatMessage>) => setMessages((all) => all.map((m) => (m.id === msg.id ? { ...m, ...p } : m)));
      patch({ voto, votoError: false });
      try {
        const ok = await sendFeedback(cred, msg.logId, voto === 'up' ? 5 : 1);
        if (!ok) patch({ voto: undefined, votoError: true });
      } catch {
        patch({ voto: undefined, votoError: true });
      }
    },
    [cred, setMessages],
  );

  const speak = useCallback(
    (msg: ChatMessage) => {
      if (speakingId === msg.id) {
        Speech.stop();
        setSpeakingId(null);
        return;
      }
      Speech.stop();
      haptic('light');
      const texto = stripMarkdown(msg.text);
      if (!texto) return;
      setSpeakingId(msg.id);
      const done = () => setSpeakingId((cur) => (cur === msg.id ? null : cur));
      const run = (language: string, fallback?: string): void =>
        Speech.speak(texto, {
          language,
          rate: 1.0,
          onDone: done,
          onStopped: done,
          onError: () => {
            if (fallback) run(fallback);
            else done();
          },
        });
      try {
        run('es-CO', 'es-ES');
      } catch {
        done();
      }
    },
    [speakingId],
  );

  const copiar = useCallback((msg: ChatMessage) => {
    haptic('select');
    // Sin librerías extra: la hoja de compartir del sistema permite copiar el texto.
    Share.share({ message: stripMarkdown(msg.text) || msg.text }).catch(() => undefined);
  }, []);

  const renderItem = ({ item }: { item: ChatMessage }) => (
    <Row item={item} c={c} speaking={speakingId === item.id} onVote={vote} onSpeak={speak} onCopy={copiar} />
  );

  const ListEmpty = (
    <View style={styles.empty}>
      <Logo size={72} />
      <Txt v="title" style={{ marginTop: spacing.md }}>
        ¿En qué te ayudo?
      </Txt>
      <Txt v="small" muted style={{ textAlign: 'center', marginTop: 4 }}>
        Pregúntame sobre tu avance, cursos, grado, competencias digitales y novedades.
      </Txt>
    </View>
  );

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.bg }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'} keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}>
      {messages.length === 0 ? (
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center' }} keyboardShouldPersistTaps="handled">
          {ListEmpty}
        </ScrollView>
      ) : (
        <FlatList
          ref={listRef}
          data={messages}
          extraData={speakingId}
          keyExtractor={(m) => m.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          onContentSizeChange={scrollEnd}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          ListFooterComponent={
            sending ? (
              <View style={styles.botRow}>
                <Avatar />
                <View style={[styles.bubble, styles.bot, { backgroundColor: c.card, borderColor: c.border }]}>
                  <TypingDots />
                </View>
              </View>
            ) : undefined
          }
        />
      )}

      <View style={{ backgroundColor: c.card, borderTopColor: c.border, borderTopWidth: StyleSheet.hairlineWidth }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} keyboardShouldPersistTaps="handled" contentContainerStyle={styles.chipsBar}>
          {SUGERENCIAS.map((s) => (
            <Pressable
              key={s}
              disabled={sending}
              onPress={() => send(s)}
              style={({ pressed }) => [
                styles.sug,
                { backgroundColor: pressed ? alpha(c.primary, 0.2) : c.primarySoft, borderColor: alpha(c.primary, 0.35), opacity: sending ? 0.5 : 1 },
              ]}
            >
              <Txt v="caption" color={c.primary} style={{ fontFamily: fonts.medium }}>
                {s}
              </Txt>
            </Pressable>
          ))}
        </ScrollView>
        <View style={styles.inputBar}>
          <TextInput
            style={[styles.input, { backgroundColor: c.inputBg, color: c.text }]}
            value={input}
            onChangeText={setInput}
            placeholder="Escribe tu pregunta..."
            placeholderTextColor={c.gray}
            multiline
            maxLength={1000}
          />
          <PressableScale onPress={() => send(input)} disabled={!input.trim() || sending} scaleTo={0.88} style={{ marginLeft: spacing.sm, opacity: !input.trim() || sending ? 0.45 : 1 }}>
            <LinearGradient colors={[brand.purple, '#6A00B0']} style={[styles.sendBtn, shadow(1, c)]}>
              <Ionicons name="send" size={18} color="#fff" style={{ marginLeft: 2 }} />
            </LinearGradient>
          </PressableScale>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function Avatar() {
  return (
    <View style={styles.avatar}>
      <Logo size={30} />
    </View>
  );
}

interface RowProps {
  item: ChatMessage;
  c: Palette;
  speaking: boolean;
  onVote: (m: ChatMessage, v: 'up' | 'down') => void;
  onSpeak: (m: ChatMessage) => void;
  onCopy: (m: ChatMessage) => void;
}

const Row = React.memo(function Row({ item, c, speaking, onVote, onSpeak, onCopy }: RowProps) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(v, { toValue: 1, duration: 240, useNativeDriver: true }).start();
  }, [v]);
  const anim = { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) }] };

  if (item.role === 'user') {
    return (
      <Animated.View style={[styles.userRow, anim]}>
        <Pressable onLongPress={() => onCopy(item)} delayLongPress={350}>
          <LinearGradient colors={[brand.purple, '#6A00B0']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[styles.bubble, styles.user]}>
            <Txt v="body" color="#fff" style={{ fontSize: 14.5, lineHeight: 21 }}>
              {item.text}
            </Txt>
            <Txt v="caption" color="rgba(255,255,255,0.7)" style={styles.time}>
              {hhmm(item.ts)}
            </Txt>
          </LinearGradient>
        </Pressable>
      </Animated.View>
    );
  }

  const intent = intentInfo(c, item.intencion, item.bloqueado);
  const blocked = !!item.bloqueado;
  const canVote = !item.esError && typeof item.logId === 'number';
  return (
    <Animated.View style={[styles.botRow, anim]}>
      <Avatar />
      <View style={{ flex: 1, alignItems: 'flex-start' }}>
        {intent ? (
          <View style={{ marginBottom: 4 }}>
            <Badge label={intent.label} color={intent.color} icon={intent.icon} small />
          </View>
        ) : null}
        <Pressable
          onLongPress={() => onCopy(item)}
          delayLongPress={350}
          style={[
            styles.bubble,
            styles.bot,
            { backgroundColor: blocked ? alpha(c.red, 0.1) : c.card, borderColor: blocked ? c.red : c.border },
            item.esError && { borderColor: alpha(c.red, 0.5) },
            shadow(1, c),
          ]}
        >
          <Markdown text={item.text} color={item.esError ? c.red : c.text} />
          <Txt v="caption" muted style={styles.time}>
            {hhmm(item.ts)}
          </Txt>
        </Pressable>

        {item.fuentes && item.fuentes.length > 0 ? (
          <View style={styles.sources}>
            {item.fuentes.map((f, i) => (
              <Pressable
                key={i}
                style={[styles.source, { backgroundColor: c.primarySoft }]}
                onPress={() => f?.url && Linking.openURL(f.url).catch(() => undefined)}
              >
                <Ionicons name="link" size={12} color={c.primary} />
                <Txt v="caption" color={c.primary} numberOfLines={1} style={{ marginLeft: 4, flexShrink: 1, fontFamily: fonts.medium }}>
                  {f?.titulo || f?.url}
                </Txt>
              </Pressable>
            ))}
          </View>
        ) : null}

        {!item.esError ? (
          <View style={styles.actions}>
            <Action
              icon={speaking ? 'stop-circle' : 'volume-high-outline'}
              color={speaking ? c.primary : c.muted}
              onPress={() => onSpeak(item)}
              label={speaking ? 'Detener lectura' : 'Escuchar respuesta'}
            />
            {canVote ? (
              <>
                <Action
                  icon={item.voto === 'up' ? 'thumbs-up' : 'thumbs-up-outline'}
                  color={item.voto === 'up' ? c.green : c.muted}
                  disabled={!!item.voto}
                  dim={item.voto === 'down'}
                  onPress={() => onVote(item, 'up')}
                  label="Respuesta útil"
                />
                <Action
                  icon={item.voto === 'down' ? 'thumbs-down' : 'thumbs-down-outline'}
                  color={item.voto === 'down' ? c.red : c.muted}
                  disabled={!!item.voto}
                  dim={item.voto === 'up'}
                  onPress={() => onVote(item, 'down')}
                  label="Respuesta no útil"
                />
              </>
            ) : null}
            {item.voto ? (
              <Txt v="caption" muted style={{ marginLeft: 4 }}>
                ¡Gracias por tu opinión!
              </Txt>
            ) : item.votoError ? (
              <Txt v="caption" color={c.red} style={{ marginLeft: 4 }}>
                No se pudo enviar. Intenta de nuevo.
              </Txt>
            ) : null}
          </View>
        ) : null}
      </View>
    </Animated.View>
  );
});

function Action({
  icon,
  color,
  onPress,
  label,
  disabled,
  dim,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  onPress: () => void;
  label: string;
  disabled?: boolean;
  dim?: boolean;
}) {
  return (
    <PressableScale onPress={onPress} disabled={disabled} scaleTo={0.8} accessibilityLabel={label} accessibilityRole="button" style={[styles.action, dim && { opacity: 0.35 }]}>
      <Ionicons name={icon} size={18} color={color} />
    </PressableScale>
  );
}

const styles = StyleSheet.create({
  list: { padding: spacing.lg, paddingBottom: spacing.sm },
  empty: { alignItems: 'center', padding: spacing.xl },
  userRow: { alignSelf: 'flex-end', maxWidth: '84%', marginBottom: spacing.md },
  botRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: spacing.md, maxWidth: '94%' },
  avatar: { marginRight: spacing.sm, marginTop: 2 },
  bubble: { borderRadius: radius.lg, paddingHorizontal: 14, paddingTop: 10, paddingBottom: 6 },
  user: { borderBottomRightRadius: 5 },
  bot: { borderBottomLeftRadius: 5, borderWidth: StyleSheet.hairlineWidth, maxWidth: '100%' },
  time: { alignSelf: 'flex-end', marginTop: 2, fontSize: 10.5, lineHeight: 14 },
  sources: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 6 },
  source: { flexDirection: 'row', alignItems: 'center', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4, marginRight: 6, marginBottom: 4, maxWidth: 240 },
  actions: { flexDirection: 'row', alignItems: 'center', marginTop: 2 },
  action: { paddingHorizontal: 8, paddingVertical: 6 },
  chipsBar: { paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  sug: { borderRadius: radius.pill, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 7, marginRight: spacing.sm },
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: spacing.md, paddingBottom: spacing.md },
  input: { flex: 1, maxHeight: 110, ...typography.body, borderRadius: 22, paddingHorizontal: 16, paddingTop: 10, paddingBottom: 10 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
});

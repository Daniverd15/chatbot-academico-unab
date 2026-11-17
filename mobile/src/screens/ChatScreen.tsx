import React, { useCallback, useRef, useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Markdown } from '../components/Markdown';
import { TypingDots } from '../components/TypingDots';
import { ApiError, sendChat } from '../api';
import { colors, radius } from '../theme';
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

export function ChatScreen({ cred, messages, setMessages }: Props) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList<ChatMessage>>(null);

  const scrollEnd = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 80);
  }, []);

  const send = useCallback(
    async (texto: string) => {
      const t = texto.trim();
      if (!t || sending) return;
      setInput('');
      setMessages((m) => [...m, { id: `u${Date.now()}`, role: 'user', text: t }]);
      setSending(true);
      scrollEnd();
      try {
        const r = await sendChat(cred, t);
        setMessages((m) => [
          ...m,
          {
            id: `b${Date.now()}`,
            role: 'bot',
            text: r.respuesta || 'No pude generar una respuesta. Intenta reformular tu pregunta.',
            fuentes: r.fuentes,
            bloqueado: r.bloqueado,
          },
        ]);
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : 'Ocurrió un error inesperado. Intenta de nuevo.';
        setMessages((m) => [...m, { id: `e${Date.now()}`, role: 'bot', text: msg }]);
      } finally {
        setSending(false);
        scrollEnd();
      }
    },
    [cred, sending, setMessages, scrollEnd],
  );

  const renderItem = ({ item }: { item: ChatMessage }) => {
    if (item.role === 'user') {
      return (
        <View style={[styles.bubble, styles.user]}>
          <Text style={styles.userText}>{item.text}</Text>
        </View>
      );
    }
    return (
      <View style={{ alignSelf: 'flex-start', maxWidth: '88%', marginBottom: 10 }}>
        <View style={[styles.bubble, styles.bot, item.bloqueado && styles.blocked, { maxWidth: '100%', marginBottom: 0 }]}>
          {item.bloqueado ? (
            <View style={styles.shieldRow}>
              <Ionicons name="shield-checkmark" size={16} color={colors.red} />
              <Text style={styles.shieldText}>Mensaje bloqueado</Text>
            </View>
          ) : null}
          <Markdown text={item.text} />
        </View>
        {item.fuentes && item.fuentes.length > 0 ? (
          <View style={styles.chips}>
            {item.fuentes.map((f, i) => (
              <Pressable key={i} style={styles.chip} onPress={() => f.url && Linking.openURL(f.url).catch(() => undefined)}>
                <Ionicons name="link" size={12} color={colors.purple} />
                <Text style={styles.chipText} numberOfLines={1}>
                  {f.titulo || f.url}
                </Text>
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      {messages.length === 0 ? (
        <ScrollView contentContainerStyle={styles.empty} keyboardShouldPersistTaps="handled">
          <Ionicons name="chatbubbles" size={44} color={colors.purple} />
          <Text style={styles.emptyTitle}>¿En qué te ayudo?</Text>
          <Text style={styles.emptySub}>Pregúntame sobre tu avance, cursos, grado, competencias digitales y novedades.</Text>
          <View style={styles.sugWrap}>
            {SUGERENCIAS.map((s) => (
              <Pressable key={s} style={styles.sug} onPress={() => send(s)}>
                <Text style={styles.sugText}>{s}</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>
      ) : (
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          onContentSizeChange={scrollEnd}
          keyboardShouldPersistTaps="handled"
          ListFooterComponent={
            sending ? (
              <View style={[styles.bubble, styles.bot]}>
                <TypingDots />
              </View>
            ) : undefined
          }
        />
      )}
      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Escribe tu pregunta..."
          placeholderTextColor={colors.gray}
          multiline
          maxLength={1000}
        />
        <Pressable
          style={[styles.sendBtn, (!input.trim() || sending) && { opacity: 0.45 }]}
          onPress={() => send(input)}
          disabled={!input.trim() || sending}
        >
          <Ionicons name="send" size={20} color={colors.white} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  list: { padding: 14, paddingBottom: 8 },
  bubble: { borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 10, marginBottom: 10, maxWidth: '88%' },
  user: { alignSelf: 'flex-end', backgroundColor: colors.purple, borderBottomRightRadius: 4 },
  userText: { color: colors.white, fontSize: 15, lineHeight: 21 },
  bot: { alignSelf: 'flex-start', backgroundColor: colors.white, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: colors.border },
  blocked: { borderColor: colors.red, backgroundColor: '#FDEEEE' },
  shieldRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  shieldText: { color: colors.red, fontWeight: '700', marginLeft: 6, fontSize: 12 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 6 },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F3E5FC',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginRight: 6,
    marginBottom: 4,
    maxWidth: 240,
  },
  chipText: { color: colors.purple, fontSize: 12, marginLeft: 4, fontWeight: '600', flexShrink: 1 },
  empty: { padding: 20, alignItems: 'center' },
  emptyTitle: { fontSize: 20, fontWeight: '800', color: colors.navy, marginTop: 8 },
  emptySub: { color: colors.muted, textAlign: 'center', marginTop: 4, marginBottom: 16 },
  sugWrap: { width: '100%' },
  sug: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.purple,
    borderRadius: radius.lg,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginBottom: 8,
  },
  sugText: { color: colors.purple, fontWeight: '600', fontSize: 14 },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 10,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  input: {
    flex: 1,
    maxHeight: 110,
    backgroundColor: colors.bg,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    fontSize: 15,
    color: colors.navy,
  },
  sendBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.purple,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
});

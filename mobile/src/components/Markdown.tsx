import React from 'react';
import { Linking, Platform, StyleSheet, Text, TextStyle, View } from 'react-native';
import { fonts, typography, useTheme } from '../theme';

const TOKEN =
  /(\[[^\]\n]+\]\(https?:\/\/[^\s)]+\)|\*\*[^*\n]+?\*\*|`[^`\n]+`|https?:\/\/[^\s)\]]+|(?<![*\w])\*(?![\s*])[^*\n]*?[^\s*]\*(?![*\w])|(?<![_\w])_(?![\s_])[^_\n]*?[^\s_]_(?![_\w]))/g;

function openUrl(url: string) {
  Linking.openURL(url).catch(() => undefined);
}

/** Quita marcas de markdown para leer el texto en voz alta. */
export function stripMarkdown(text: string): string {
  return (text ?? '')
    .replace(/\r/g, '')
    .replace(/\[([^\]\n]+)\]\(https?:\/\/[^\s)]+\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/^\s*#{1,6}\s+/gm, '')
    .replace(/^\s*[-*•]\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/[*_`~>]/g, '')
    .replace(/\n{2,}/g, '. ')
    .replace(/\n/g, '. ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

export function Markdown({ text, color }: { text: string; color?: string }) {
  const { c } = useTheme();
  const fg = color ?? c.text;
  const base: TextStyle = { color: fg };

  const renderInline = (t: string, keyPrefix: string): React.ReactNode[] =>
    t
      .split(TOKEN)
      .filter((p) => p !== '')
      .map((p, i) => {
        const key = `${keyPrefix}-${i}`;
        if (p.startsWith('**') && p.endsWith('**') && p.length > 4) {
          return (
            <Text key={key} style={styles.bold}>
              {renderInline(p.slice(2, -2), `${key}b`)}
            </Text>
          );
        }
        if (p.length > 2 && p.startsWith('`') && p.endsWith('`')) {
          return (
            <Text key={key} style={[styles.code, { backgroundColor: c.border }]}>
              {` ${p.slice(1, -1)} `}
            </Text>
          );
        }
        if (p.length > 2 && ((p.startsWith('*') && p.endsWith('*')) || (p.startsWith('_') && p.endsWith('_')))) {
          return (
            <Text key={key} style={styles.italic}>
              {renderInline(p.slice(1, -1), `${key}i`)}
            </Text>
          );
        }
        const mdLink = /^\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(p);
        if (mdLink) {
          const [, label, url] = mdLink;
          return (
            <Text key={key} style={[styles.link, { color: c.primary }]} onPress={() => openUrl(url)} accessibilityRole="link">
              {label}
            </Text>
          );
        }
        if (/^https?:\/\//.test(p)) {
          const clean = p.replace(/[.,;:!?]+$/, '');
          const tail = p.slice(clean.length);
          return (
            <Text key={key}>
              <Text style={[styles.link, { color: c.primary }]} onPress={() => openUrl(clean)}>
                {clean}
              </Text>
              {tail}
            </Text>
          );
        }
        return <Text key={key}>{p}</Text>;
      });

  const lines = (text ?? '').replace(/\r/g, '').split('\n');
  return (
    <View>
      {lines.map((raw, i) => {
        const line = raw.trimEnd();
        if (line.trim() === '') return <View key={i} style={{ height: 6 }} />;
        if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) {
          return <View key={i} style={[styles.hr, { backgroundColor: c.border }]} />;
        }
        const bullet = /^\s*([-*•])\s+(.*)$/.exec(line);
        if (bullet) {
          return (
            <View key={i} style={styles.itemRow}>
              <Text style={[styles.text, base, styles.marker, { color: c.primary }]}>•</Text>
              <Text style={[styles.text, base, styles.itemText]}>{renderInline(bullet[2], `b${i}`)}</Text>
            </View>
          );
        }
        const num = /^\s*(\d+)[.)]\s+(.*)$/.exec(line);
        if (num) {
          return (
            <View key={i} style={styles.itemRow}>
              <Text style={[styles.text, base, styles.marker, { color: c.primary }]}>{num[1]}.</Text>
              <Text style={[styles.text, base, styles.itemText]}>{renderInline(num[2], `n${i}`)}</Text>
            </View>
          );
        }
        const heading = /^\s*#{1,6}\s+(.*)$/.exec(line);
        if (heading) {
          return (
            <Text key={i} style={[styles.text, base, styles.bold, { marginTop: 4 }]}>
              {renderInline(heading[1], `h${i}`)}
            </Text>
          );
        }
        return (
          <Text key={i} style={[styles.text, base]}>
            {renderInline(line, `p${i}`)}
          </Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  text: { ...typography.body, fontSize: 14.5, lineHeight: 22 },
  bold: { fontFamily: fonts.semibold },
  italic: { fontStyle: 'italic' },
  code: { fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier', fontSize: 13 },
  hr: { height: 1, marginVertical: 8 },
  link: { textDecorationLine: 'underline' },
  itemRow: { flexDirection: 'row', paddingLeft: 2 },
  marker: { width: 20 },
  itemText: { flex: 1 },
});

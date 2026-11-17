import React from 'react';
import { Linking, StyleSheet, Text, TextStyle, View } from 'react-native';
import { colors } from '../theme';

const TOKEN = /(\*\*[^*]+\*\*|https?:\/\/[^\s)\]]+)/g;

function openUrl(url: string) {
  Linking.openURL(url).catch(() => undefined);
}

function renderInline(text: string, base: TextStyle, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(TOKEN);
  return parts
    .filter((p) => p !== '')
    .map((p, i) => {
      const key = `${keyPrefix}-${i}`;
      if (p.startsWith('**') && p.endsWith('**') && p.length > 4) {
        return (
          <Text key={key} style={styles.bold}>
            {p.slice(2, -2)}
          </Text>
        );
      }
      if (/^https?:\/\//.test(p)) {
        const clean = p.replace(/[.,;:!?]+$/, '');
        const tail = p.slice(clean.length);
        return (
          <Text key={key}>
            <Text style={styles.link} onPress={() => openUrl(clean)}>
              {clean}
            </Text>
            {tail}
          </Text>
        );
      }
      return <Text key={key}>{p}</Text>;
    });
}

export function Markdown({ text, color = colors.navy }: { text: string; color?: string }) {
  const base: TextStyle = { color };
  const lines = (text ?? '').replace(/\r/g, '').split('\n');
  return (
    <View>
      {lines.map((raw, i) => {
        const line = raw.trimEnd();
        if (line.trim() === '') return <View key={i} style={{ height: 6 }} />;
        const bullet = /^\s*([-*•])\s+(.*)$/.exec(line);
        if (bullet) {
          return (
            <View key={i} style={styles.itemRow}>
              <Text style={[styles.text, base, styles.marker]}>•</Text>
              <Text style={[styles.text, base, styles.itemText]}>{renderInline(bullet[2], base, `b${i}`)}</Text>
            </View>
          );
        }
        const num = /^\s*(\d+)[.)]\s+(.*)$/.exec(line);
        if (num) {
          return (
            <View key={i} style={styles.itemRow}>
              <Text style={[styles.text, base, styles.marker]}>{num[1]}.</Text>
              <Text style={[styles.text, base, styles.itemText]}>{renderInline(num[2], base, `n${i}`)}</Text>
            </View>
          );
        }
        const heading = /^\s*#{1,6}\s+(.*)$/.exec(line);
        if (heading) {
          return (
            <Text key={i} style={[styles.text, base, styles.bold]}>
              {renderInline(heading[1], base, `h${i}`)}
            </Text>
          );
        }
        return (
          <Text key={i} style={[styles.text, base]}>
            {renderInline(line, base, `p${i}`)}
          </Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  text: { fontSize: 15, lineHeight: 21 },
  bold: { fontWeight: '700' },
  link: { color: colors.purple, textDecorationLine: 'underline' },
  itemRow: { flexDirection: 'row', paddingLeft: 4 },
  marker: { width: 22 },
  itemText: { flex: 1 },
});

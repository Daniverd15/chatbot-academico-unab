import * as Haptics from 'expo-haptics';

/** Retroalimentación háptica segura (nunca lanza). */
export function haptic(kind: 'light' | 'select' | 'success' | 'warning' = 'light'): void {
  try {
    if (kind === 'select') Haptics.selectionAsync().catch(() => undefined);
    else if (kind === 'success') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => undefined);
    else if (kind === 'warning') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => undefined);
    else Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => undefined);
  } catch {
    // ignorar
  }
}

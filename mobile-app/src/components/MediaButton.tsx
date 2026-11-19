import type { ReactNode } from 'react';
import { Text, TouchableOpacity, type StyleProp, type TextStyle, type ViewStyle } from 'react-native';

type Props = { label: ReactNode; accessibilityLabel: string; disabled: boolean; onPress: () => void; style: StyleProp<ViewStyle>; textStyle: StyleProp<TextStyle> };

export function MediaButton({ label, accessibilityLabel, disabled, onPress, style, textStyle }: Props) {
  return <TouchableOpacity accessibilityRole="button" accessibilityLabel={accessibilityLabel} disabled={disabled} activeOpacity={.55} style={[style, disabled && { opacity: .4 }]} onPress={onPress}><Text style={textStyle}>{label}</Text></TouchableOpacity>;
}

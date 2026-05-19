import { V4Stat, type V4StatIcon, type V4StatIconTone } from "@/components/ui/v4/v4-stat";

interface WidgetStatProps {
  label: string;
  value: string;
  caption?: string;
  icon: V4StatIcon;
  iconTone?: V4StatIconTone;
}

/** Legacy name — delegates to Hive Control V4 stat tile. */
export function WidgetStat({ label, value, caption, icon, iconTone = "default" }: WidgetStatProps) {
  return <V4Stat label={label} value={value} icon={icon} iconTone={iconTone} foot={caption} />;
}

import type { WatchCompletion } from '../lib/types';
import { useMoodTheme } from '../features/mood/MoodThemeContext';

interface WatchCompletionPickerProps {
  value: WatchCompletion | null;
  onChange: (v: WatchCompletion | null) => void;
  accentColor?: string;
}

const OPTIONS: { key: WatchCompletion; label: string; pct: number }[] = [
  { key: 'barely',   label: 'Barely',   pct: 5  },
  { key: 'half',     label: 'Half',     pct: 50 },
  { key: 'mostly',   label: 'Almost',   pct: 75 },
  { key: 'finished', label: 'Finished', pct: 100 },
];

function ProgressBar({ pct, active, accent, isDark }: { pct: number; active: boolean; accent: string; isDark: boolean }) {
  const trackFill = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
  const inactiveFill = isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.2)';
  return (
    <svg width="24" height="8" viewBox="0 0 24 8" fill="none" aria-hidden="true">
      <rect x="0" y="2" width="24" height="4" rx="2" fill={trackFill} />
      <rect x="0" y="2" width={Math.round(24 * pct / 100)} height="4" rx="2" fill={active ? accent : inactiveFill} />
    </svg>
  );
}

export function WatchCompletionPicker({ value, onChange, accentColor = '#6366f1' }: WatchCompletionPickerProps) {
  const { isDark } = useMoodTheme();
  const inactiveBorder = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.12)';
  const inactiveColor = isDark ? '#94a3b8' : '#6b7280';

  return (
    <div className="grid grid-cols-4 gap-1">
      {OPTIONS.map(({ key, label, pct }) => {
        const active = value === key;
        return (
          <button
            key={key}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(active ? null : key)}
            className="flex flex-col items-center gap-1 rounded-lg py-1.5 px-1 text-[10px] font-bold transition-all duration-200 border"
            style={{
              borderColor: active ? accentColor : inactiveBorder,
              background: active ? `${accentColor}22` : 'transparent',
              color: active ? accentColor : inactiveColor,
            }}
          >
            <ProgressBar pct={pct} active={active} accent={accentColor} isDark={isDark} />
            {label}
          </button>
        );
      })}
    </div>
  );
}

export default WatchCompletionPicker;

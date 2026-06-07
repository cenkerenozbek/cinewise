import type { WatchCompletion } from '../lib/types';

interface WatchCompletionPickerProps {
  value: WatchCompletion | null;
  onChange: (v: WatchCompletion) => void;
  accentColor?: string;
}

const OPTIONS: { key: WatchCompletion; label: string; pct: number }[] = [
  { key: 'barely',   label: 'Barely',   pct: 5  },
  { key: 'half',     label: 'Half',     pct: 50 },
  { key: 'mostly',   label: 'Almost',   pct: 75 },
  { key: 'finished', label: 'Finished', pct: 100 },
];

function ProgressBar({ pct, active, accent }: { pct: number; active: boolean; accent: string }) {
  return (
    <svg width="24" height="8" viewBox="0 0 24 8" fill="none" aria-hidden="true">
      <rect x="0" y="2" width="24" height="4" rx="2" fill="rgba(255,255,255,0.1)" />
      <rect x="0" y="2" width={Math.round(24 * pct / 100)} height="4" rx="2" fill={active ? accent : 'rgba(255,255,255,0.25)'} />
    </svg>
  );
}

export function WatchCompletionPicker({ value, onChange, accentColor = '#6366f1' }: WatchCompletionPickerProps) {
  return (
    <div className="grid grid-cols-4 gap-1">
      {OPTIONS.map(({ key, label, pct }) => {
        const active = value === key;
        return (
          <button
            key={key}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(key)}
            className="flex flex-col items-center gap-1 rounded-lg py-1.5 px-1 text-[10px] font-bold transition-all duration-200 border"
            style={{
              borderColor: active ? accentColor : 'rgba(255,255,255,0.08)',
              background: active ? `${accentColor}22` : 'transparent',
              color: active ? accentColor : '#94a3b8',
            }}
          >
            <ProgressBar pct={pct} active={active} accent={accentColor} />
            {label}
          </button>
        );
      })}
    </div>
  );
}

export default WatchCompletionPicker;

const MOODS = ['Happy', 'Tense', 'Relaxing', 'Mind-bending', 'Romantic'];

const MOOD_META: Record<string, { icon: string; color: string }> = {
  Happy:          { color: '#f59e0b', icon: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z' },
  Tense:          { color: '#2dd4bf', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  Relaxing:       { color: '#b8a4ed', icon: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z' },
  'Mind-bending': { color: '#a855f7', icon: 'M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z' },
  Romantic:       { color: '#fb7185', icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z' },
};

interface PreferenceChipProps {
  label: string;
  selected: boolean;
  onClick: () => void;
}

export function PreferenceChip({ label, selected, onClick }: PreferenceChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className="relative rounded-full px-3.5 py-1.5 text-xs font-medium transition-all duration-200 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 border overflow-hidden"
      style={
        selected
          ? {
              background: 'linear-gradient(135deg, var(--cw-accent), color-mix(in srgb, var(--cw-accent) 70%, #a855f7))',
              borderColor: 'transparent',
              color: '#ffffff',
              boxShadow: '0 0 12px color-mix(in srgb, var(--cw-accent) 50%, transparent)',
            }
          : {
              background: 'var(--cw-surface-elevated)',
              borderColor: 'rgba(255,255,255,0.07)',
              color: '#64748b',
            }
      }
    >
      {label}
    </button>
  );
}

interface GenreChipGroupProps {
  genres: string[];
  selected: string[];
  onToggle: (genre: string) => void;
}

export function GenreChipGroup({ genres, selected, onToggle }: GenreChipGroupProps) {
  return (
    <div role="group" aria-label="Genre selection" className="flex flex-wrap gap-1.5 mt-3">
      {genres.map((genre) => (
        <PreferenceChip
          key={genre}
          label={genre}
          selected={selected.includes(genre)}
          onClick={() => onToggle(genre)}
        />
      ))}
    </div>
  );
}

interface MoodChipGroupProps {
  selected: string | null;
  onSelect: (mood: string | null) => void;
}

export function MoodChipGroup({ selected, onSelect }: MoodChipGroupProps) {
  return (
    <div role="radiogroup" aria-label="Mood selection (optional)" className="flex flex-wrap gap-2 mt-3">
      {MOODS.map((mood) => {
        const { color, icon } = MOOD_META[mood];
        const active = selected === mood;
        return (
          <button
            key={mood}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(active ? null : mood)}
            className="group relative flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all duration-200 cursor-pointer border overflow-hidden"
            style={
              active
                ? {
                    background: `linear-gradient(135deg, ${color}ee, ${color}88)`,
                    borderColor: 'transparent',
                    color: '#fff',
                    boxShadow: `0 0 14px ${color}50`,
                  }
                : {
                    background: 'var(--cw-surface-elevated)',
                    borderColor: `${color}30`,
                    color: '#64748b',
                  }
            }
          >
            {!active && (
              <span
                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                style={{ background: `${color}12` }}
              />
            )}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-3.5 w-3.5 shrink-0 z-10"
              fill="none"
              viewBox="0 0 24 24"
              stroke={active ? '#fff' : color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d={icon} />
            </svg>
            <span className="z-10">{mood}</span>
          </button>
        );
      })}
    </div>
  );
}

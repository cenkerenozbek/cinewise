const MOODS = ['Happy', 'Tense', 'Relaxing', 'Mind-bending', 'Romantic'];

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
      className="min-h-[44px] sm:min-h-0 rounded-full px-4 py-2 text-sm font-normal transition-all duration-200 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 border"
      style={
        selected
          ? {
              background: 'var(--cw-accent)',
              borderColor: 'var(--cw-accent)',
              color: '#ffffff',
            }
          : {
              background: 'var(--cw-surface-elevated)',
              borderColor: 'var(--cw-border)',
              color: '#94a3b8',
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
    <div role="group" aria-label="Genre selection" className="flex flex-wrap gap-2 mt-2">
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

const MOOD_ICONS: Record<string, string> = {
  Happy:        'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  Tense:        'M13 10V3L4 14h7v7l9-11h-7z',
  Relaxing:     'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z',
  'Mind-bending': 'M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z',
  Romantic:     'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
};

export function MoodChipGroup({ selected, onSelect }: MoodChipGroupProps) {
  return (
    <div role="radiogroup" aria-label="Mood selection (optional)" className="flex flex-wrap gap-2 mt-2">
      {MOODS.map((mood) => (
        <button
          key={mood}
          type="button"
          aria-pressed={selected === mood}
          onClick={() => onSelect(selected === mood ? null : mood)}
          className="min-h-[44px] sm:min-h-0 rounded-full px-4 py-2 text-sm font-normal transition-all duration-200 cursor-pointer border flex items-center gap-1.5"
          style={
            selected === mood
              ? {
                  background: 'var(--cw-accent)',
                  borderColor: 'var(--cw-accent)',
                  color: '#ffffff',
                }
              : {
                  background: 'var(--cw-surface-elevated)',
                  borderColor: 'var(--cw-border)',
                  color: '#94a3b8',
                }
          }
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d={MOOD_ICONS[mood]} />
          </svg>
          {mood}
        </button>
      ))}
    </div>
  );
}

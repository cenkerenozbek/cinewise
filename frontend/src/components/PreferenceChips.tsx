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
      className="min-h-[44px] sm:min-h-0 rounded-full px-4 py-2 text-sm font-bold transition-all duration-200 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 border"
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

const MOOD_EMOJIS: Record<string, string> = {
  Happy: '😄',
  Tense: '😬',
  Relaxing: '😌',
  'Mind-bending': '🌀',
  Romantic: '❤️',
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
          className="min-h-[44px] sm:min-h-0 rounded-full px-4 py-2 text-sm font-bold transition-all duration-200 cursor-pointer border flex items-center gap-1.5"
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
          <span>{MOOD_EMOJIS[mood] ?? ''}</span>
          {mood}
        </button>
      ))}
    </div>
  );
}

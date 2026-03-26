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
      className={`min-h-[44px] sm:min-h-0 rounded-full px-4 py-2 text-sm font-bold transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 ${
        selected
          ? 'bg-blue-600 border border-blue-600 text-white hover:bg-blue-700'
          : 'bg-white border border-gray-300 text-gray-700 hover:border-blue-400 hover:text-blue-600'
      }`}
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

export function MoodChipGroup({ selected, onSelect }: MoodChipGroupProps) {
  return (
    <div role="radiogroup" aria-label="Mood selection (optional)" className="flex flex-wrap gap-2 mt-2">
      {MOODS.map((mood) => (
        <PreferenceChip
          key={mood}
          label={mood}
          selected={selected === mood}
          onClick={() => onSelect(selected === mood ? null : mood)}
        />
      ))}
    </div>
  );
}

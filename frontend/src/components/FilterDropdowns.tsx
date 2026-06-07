import { useGenres } from '../hooks/useMovies';

interface FilterDropdownsProps {
  genre: string;
  year: string;
  onGenreChange: (genre: string) => void;
  onYearChange: (year: string) => void;
}

function getYearOptions(): number[] {
  const currentYear = new Date().getFullYear();
  const years: number[] = [];
  for (let y = currentYear; y >= 1970; y--) {
    years.push(y);
  }
  return years;
}

const selectStyle = {
  background: 'var(--cw-surface)',
  borderColor: 'var(--cw-border)',
  color: '#94a3b8',
};

export function FilterDropdowns({ genre, year, onGenreChange, onYearChange }: FilterDropdownsProps) {
  const { data: genres } = useGenres();

  return (
    <div className="flex gap-2">
      <select
        value={genre}
        onChange={(e) => onGenreChange(e.target.value)}
        className="px-3 py-2.5 border rounded-xl text-sm focus:outline-none focus:ring-2 transition-all"
        style={selectStyle}
      >
        <option value="">All Genres</option>
        {genres?.map((g) => (
          <option key={g} value={g}>{g}</option>
        ))}
      </select>
      <select
        value={year}
        onChange={(e) => onYearChange(e.target.value)}
        className="px-3 py-2.5 border rounded-xl text-sm focus:outline-none focus:ring-2 transition-all"
        style={selectStyle}
      >
        <option value="">All Years</option>
        {getYearOptions().map((y) => (
          <option key={y} value={String(y)}>{y}</option>
        ))}
      </select>
    </div>
  );
}

export default FilterDropdowns;

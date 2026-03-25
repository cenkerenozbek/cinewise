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

export function FilterDropdowns({ genre, year, onGenreChange, onYearChange }: FilterDropdownsProps) {
  const { data: genres } = useGenres();

  return (
    <div className="flex gap-2">
      <select
        value={genre}
        onChange={(e) => onGenreChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Genres</option>
        {genres?.map((g) => (
          <option key={g} value={g}>
            {g}
          </option>
        ))}
      </select>
      <select
        value={year}
        onChange={(e) => onYearChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Years</option>
        {getYearOptions().map((y) => (
          <option key={y} value={String(y)}>
            {y}
          </option>
        ))}
      </select>
    </div>
  );
}

export default FilterDropdowns;

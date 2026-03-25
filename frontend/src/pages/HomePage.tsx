import { useState } from 'react';
import { useMovieSearch } from '../hooks/useMovies';
import { SearchBar } from '../components/SearchBar';
import { MovieGrid } from '../components/MovieGrid';
import { FilterDropdowns } from '../components/FilterDropdowns';

export function HomePage() {
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('');
  const [year, setYear] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useMovieSearch(query, genre, year, page);

  const movies = data?.movies ?? [];
  const total = data?.total ?? 0;
  const pageSize = data?.page_size ?? 20;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const isSearching = !!query || !!genre || !!year;

  function handleSearchChange(value: string) {
    setQuery(value);
    setPage(1);
  }

  function handleGenreChange(value: string) {
    setGenre(value);
    setPage(1);
  }

  function handleYearChange(value: string) {
    setYear(value);
    setPage(1);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">
        {isSearching ? 'Search Results' : 'Popular Movies'}
      </h1>
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <SearchBar value={query} onChange={handleSearchChange} />
        <FilterDropdowns
          genre={genre}
          year={year}
          onGenreChange={handleGenreChange}
          onYearChange={handleYearChange}
        />
      </div>
      <MovieGrid movies={movies} isLoading={isLoading} />
      {!isLoading && total > 0 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 text-sm font-medium bg-white border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 text-sm font-medium bg-white border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default HomePage;

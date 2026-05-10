import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMovieSearch } from '../hooks/useMovies';
import { useRecommendations, useUserPreferences } from '../hooks/useRecommendations';
import { SearchBar } from '../components/SearchBar';
import { MovieGrid } from '../components/MovieGrid';
import { FilterDropdowns } from '../components/FilterDropdowns';
import { RecommendationCard } from '../components/RecommendationCard';
import { useAuth } from '../hooks/useAuth';
import { useFeedback } from '../hooks/useFeedback';
import type { FeedbackAction } from '../lib/types';

export function HomePage() {
  const { isAuthenticated, user } = useAuth();
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('');
  const [year, setYear] = useState('');
  const [page, setPage] = useState(1);
  const [votes, setVotes] = useState<Map<number, FeedbackAction>>(new Map());

  const { data, isLoading } = useMovieSearch(query, genre, year, page);
  const { data: savedPrefs, isLoading: prefsLoading } = useUserPreferences(
    isAuthenticated,
    user?.id ?? 'anonymous',
  );
  const { mutate: submitFeedback } = useFeedback();

  const movies = data?.movies ?? [];
  const total = data?.total ?? 0;
  const pageSize = data?.page_size ?? 20;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const isSearching = !!query || !!genre || !!year;
  const hasSavedPreferences = Boolean(savedPrefs && savedPrefs.genres.length > 0);
  const shouldShowPersonalized = isAuthenticated && hasSavedPreferences && !isSearching;
  const {
    data: personalizedData,
    isLoading: personalizedLoading,
    isError: personalizedError,
  } = useRecommendations(
    shouldShowPersonalized ? savedPrefs?.genres ?? [] : [],
    shouldShowPersonalized ? savedPrefs?.mood ?? null : null,
    user?.id ?? 'anonymous',
  );

  const personalizedRecommendations = personalizedData?.recommendations ?? [];

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

  function handleVote(tmdbId: number, action: FeedbackAction) {
    const prev = votes.get(tmdbId) ?? null;
    setVotes((m) => new Map(m).set(tmdbId, action));
    submitFeedback(
      { movie_id: tmdbId, action },
      {
        onError: () => {
          if (prev) {
            setVotes((m) => new Map(m).set(tmdbId, prev));
          } else {
            setVotes((m) => {
              const next = new Map(m);
              next.delete(tmdbId);
              return next;
            });
          }
        },
      },
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {shouldShowPersonalized && (
        <section className="mb-8">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">For You</h1>
              <p className="text-sm text-gray-500">
                {savedPrefs?.genres.join(', ')}
                {savedPrefs?.mood ? ` / ${savedPrefs.mood}` : ''}
              </p>
            </div>
            <Link
              to="/recommendations"
              className="inline-flex h-10 items-center justify-center rounded-md bg-gray-900 px-4 text-sm font-bold text-white hover:bg-gray-800"
            >
              Edit Preferences
            </Link>
          </div>

          {personalizedLoading && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="rounded-lg overflow-hidden bg-white shadow animate-pulse">
                  <div className="aspect-[2/3] bg-gray-300" />
                  <div className="p-2 space-y-2">
                    <div className="h-3 bg-gray-300 rounded w-3/4" />
                    <div className="h-2 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!personalizedLoading && personalizedError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              Could not load personalized recommendations right now.
            </div>
          )}

          {!personalizedLoading && !personalizedError && personalizedRecommendations.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {personalizedRecommendations.slice(0, 5).map((item) => (
                <RecommendationCard
                  key={item.tmdb_id}
                  item={item}
                  vote={votes.get(item.tmdb_id)}
                  onVote={handleVote}
                  showFeedback={isAuthenticated}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {isAuthenticated && !prefsLoading && !hasSavedPreferences && !isSearching && (
        <div className="mb-6 flex flex-col gap-3 rounded-lg border border-blue-100 bg-blue-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-medium text-blue-900">No saved preferences yet.</p>
          <Link
            to="/recommendations"
            className="inline-flex h-10 items-center justify-center rounded-md bg-blue-600 px-4 text-sm font-bold text-white hover:bg-blue-700"
          >
            Set Preferences
          </Link>
        </div>
      )}

      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        {isSearching ? 'Search Results' : shouldShowPersonalized ? 'Browse Movies' : 'Popular Movies'}
      </h2>
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

import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMovieSearch } from '../hooks/useMovies';
import { useRecommendations, useUserPreferences } from '../hooks/useRecommendations';
import { MovieGrid } from '../components/MovieGrid';
import { FilterDropdowns } from '../components/FilterDropdowns';
import { RecommendationCard } from '../components/RecommendationCard';
import { useAuth } from '../hooks/useAuth';
import { useFeedback } from '../hooks/useFeedback';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import type { FeedbackAction } from '../lib/types';

export function HomePage() {
  const { isAuthenticated, user } = useAuth();
  const { setActiveMood } = useMoodTheme();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';
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

  // Apply saved mood to theme on load
  if (savedPrefs?.mood) {
    setActiveMood(savedPrefs.mood);
  }

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

  // Reset to page 1 whenever the search query changes from the navbar
  useEffect(() => { setPage(1); }, [query]);

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
    <div className="min-h-screen">
      {/* Hero section — shown only to unauthenticated users who aren't searching */}
      {!isAuthenticated && !isSearching && (
        <div
          className="w-full py-20 px-4 mb-8"
          style={{
            background: 'linear-gradient(180deg, var(--cw-surface) 0%, var(--cw-bg) 100%)',
          }}
        >
          <div className="max-w-3xl mx-auto text-center">
            <div
              className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest px-3 py-1.5 rounded-full border mb-6"
              style={{ borderColor: 'var(--cw-accent)', color: 'var(--cw-accent)', background: 'var(--cw-accent)11' }}
            >
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--cw-accent)' }} />
              AI-Powered Recommendations
            </div>
            <h1 className="text-4xl sm:text-5xl font-black text-slate-100 leading-tight tracking-tight mb-4">
              Discover Your Next<br />
              <span style={{ color: 'var(--cw-accent)' }}>Favorite Film</span>
            </h1>
            <p className="text-lg text-slate-400 mb-8 max-w-xl mx-auto">
              A hybrid recommendation engine that learns your taste — combining semantic embeddings with collaborative filtering.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link
                to="/register"
                className="px-6 py-3 rounded-xl font-bold text-white transition-opacity hover:opacity-90"
                style={{ background: 'var(--cw-accent)' }}
              >
                Get Recommendations
              </Link>
              <a
                href="#browse"
                className="px-6 py-3 rounded-xl font-bold border transition-all"
                style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
              >
                Browse Movies
              </a>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Personalized section */}
        {shouldShowPersonalized && (
          <section className="mb-8">
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-100">For You</h1>
                <p className="text-sm text-slate-400">
                  {savedPrefs?.genres.join(', ')}
                  {savedPrefs?.mood ? (
                    <span
                      className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold border"
                      style={{ borderColor: 'var(--cw-accent)', color: 'var(--cw-accent)', background: 'var(--cw-accent)15' }}
                    >
                      {savedPrefs.mood}
                    </span>
                  ) : null}
                </p>
              </div>
              <Link
                to="/recommendations"
                className="inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-bold text-white transition-opacity hover:opacity-90"
                style={{ background: 'var(--cw-accent)' }}
              >
                Edit Preferences
              </Link>
            </div>

            {personalizedLoading && (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="rounded-xl overflow-hidden skeleton">
                    <div className="aspect-[2/3]" />
                    <div className="p-2.5 space-y-2">
                      <div className="h-3 rounded w-3/4" style={{ background: 'var(--cw-surface-elevated)' }} />
                      <div className="h-2 rounded w-1/2" style={{ background: 'var(--cw-surface-elevated)' }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!personalizedLoading && personalizedError && (
              <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
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

        {/* No preferences prompt */}
        {isAuthenticated && !prefsLoading && !hasSavedPreferences && !isSearching && (
          <div
            className="mb-6 flex flex-col gap-3 rounded-xl border px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
            style={{ borderColor: 'var(--cw-accent)33', background: 'var(--cw-accent)11' }}
          >
            <p className="text-sm font-medium text-slate-300">
              Set your preferences to get personalized recommendations.
            </p>
            <Link
              to="/recommendations"
              className="inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-bold text-white transition-opacity hover:opacity-90 shrink-0"
              style={{ background: 'var(--cw-accent)' }}
            >
              Set Preferences
            </Link>
          </div>
        )}

        <div id="browse">
          <h2 className="text-xl font-bold text-slate-100 mb-4">
            {isSearching ? 'Search Results' : shouldShowPersonalized ? 'Browse Movies' : 'Popular Movies'}
          </h2>
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
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
                className="px-4 py-2 text-sm font-medium border rounded-xl disabled:opacity-40 transition-colors"
                style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
              >
                Previous
              </button>
              <span className="text-sm text-slate-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-4 py-2 text-sm font-medium border rounded-xl disabled:opacity-40 transition-colors"
                style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default HomePage;

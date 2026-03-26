import { useState, useEffect } from 'react';
import { useRecommendations, useUserPreferences } from '../hooks/useRecommendations';
import { useGenres } from '../hooks/useMovies';
import { MovieCard } from '../components/MovieCard';
import { GenreChipGroup, MoodChipGroup } from '../components/PreferenceChips';
import { useFeedback } from '../hooks/useFeedback';
import { useAuth } from '../hooks/useAuth';
import type { MovieSummary, RecommendationItem, FeedbackAction } from '../lib/types';

function SkeletonCard() {
  return (
    <div className="rounded-lg overflow-hidden bg-white shadow animate-pulse">
      <div className="aspect-[2/3] bg-gray-300" />
      <div className="p-2 space-y-2">
        <div className="h-3 bg-gray-300 rounded w-3/4" />
        <div className="h-2 bg-gray-200 rounded w-1/2" />
      </div>
    </div>
  );
}

function toMovieSummary(item: RecommendationItem): MovieSummary {
  return {
    tmdb_id: item.tmdb_id,
    title: item.title,
    title_tr: item.title_tr,
    year: item.year,
    genres: item.genres,
    poster_path: item.poster_path,
    rating: item.rating,
  };
}

interface PreferenceFormProps {
  availableGenres: string[];
  selectedGenres: string[];
  selectedMood: string | null;
  onGenreToggle: (genre: string) => void;
  onMoodSelect: (mood: string | null) => void;
  onSubmit: () => void;
  submitLabel: string;
  showValidationError: boolean;
}

function PreferenceForm({
  availableGenres,
  selectedGenres,
  selectedMood,
  onGenreToggle,
  onMoodSelect,
  onSubmit,
  submitLabel,
  showValidationError,
}: PreferenceFormProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="space-y-6">
        <div>
          <p className="text-sm font-bold text-gray-700">Select Genres</p>
          <GenreChipGroup
            genres={availableGenres}
            selected={selectedGenres}
            onToggle={onGenreToggle}
          />
          {showValidationError && (
            <p className="text-sm text-red-600 mt-1">Please select at least one genre.</p>
          )}
        </div>
        <div>
          <p className="text-sm font-bold text-gray-700">
            How are you feeling?{' '}
            <span className="text-xs text-gray-400 font-normal">(optional)</span>
          </p>
          <MoodChipGroup selected={selectedMood} onSelect={onMoodSelect} />
        </div>
      </div>
      <button
        type="button"
        onClick={onSubmit}
        disabled={selectedGenres.length === 0}
        className="mt-6 w-full py-2 px-4 bg-blue-600 text-white font-bold rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {submitLabel}
      </button>
    </div>
  );
}

export function RecommendationsPage() {
  const { data: savedPrefs, isLoading: prefsLoading } = useUserPreferences();
  const { data: genresData } = useGenres();
  const { isAuthenticated } = useAuth();

  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [submittedGenres, setSubmittedGenres] = useState<string[]>([]);
  const [submittedMood, setSubmittedMood] = useState<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [showValidationError, setShowValidationError] = useState(false);
  const [votes, setVotes] = useState<Map<number, FeedbackAction>>(new Map());
  const { mutate: submitFeedback } = useFeedback();

  const availableGenres = genresData ?? [];

  // Populate from saved preferences on mount
  useEffect(() => {
    if (savedPrefs && savedPrefs.genres.length > 0) {
      setSelectedGenres(savedPrefs.genres);
      setSelectedMood(savedPrefs.mood);
      setSubmittedGenres(savedPrefs.genres);
      setSubmittedMood(savedPrefs.mood);
      setHasSubmitted(true);
    }
  }, [savedPrefs]);

  const {
    data: recommendationData,
    isLoading: recsLoading,
    isError,
    error: recsError,
    refetch,
  } = useRecommendations(
    hasSubmitted ? submittedGenres : [],
    hasSubmitted ? submittedMood : null
  );

  function handleGenreToggle(genre: string) {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
    setShowValidationError(false);
  }

  function handleSubmit() {
    if (selectedGenres.length === 0) {
      setShowValidationError(true);
      return;
    }
    setShowValidationError(false);
    setSubmittedGenres(selectedGenres);
    setSubmittedMood(selectedMood);
    setHasSubmitted(true);
    setShowForm(false);
  }

  function handleVote(tmdbId: number, action: FeedbackAction) {
    const prev = votes.get(tmdbId) ?? null;
    setVotes((m) => new Map(m).set(tmdbId, action));
    submitFeedback(
      { movie_id: tmdbId, action },
      {
        onError: () => {
          // Revert on failure
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
      }
    );
  }

  const recommendations = recommendationData?.recommendations ?? [];

  // State A: no preferences submitted yet (and no saved prefs loading)
  if (!hasSubmitted && !prefsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Your Recommendations</h1>
        <div className="max-w-xl">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            What kind of movies do you enjoy?
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            Select at least one genre to get personalized recommendations.
          </p>
          <PreferenceForm
            availableGenres={availableGenres}
            selectedGenres={selectedGenres}
            selectedMood={selectedMood}
            onGenreToggle={handleGenreToggle}
            onMoodSelect={setSelectedMood}
            onSubmit={handleSubmit}
            submitLabel="Get My Recommendations"
            showValidationError={showValidationError}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Your Recommendations</h1>

      {/* EditPreferencesControl */}
      <div className="mb-4">
        <button
          type="button"
          onClick={() => setShowForm((prev) => !prev)}
          className="px-4 py-2 text-sm font-bold bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          {showForm ? 'Update Recommendations' : 'Edit Preferences'}
        </button>
        {showForm && (
          <div className="mt-4">
            <PreferenceForm
              availableGenres={availableGenres}
              selectedGenres={selectedGenres}
              selectedMood={selectedMood}
              onGenreToggle={handleGenreToggle}
              onMoodSelect={setSelectedMood}
              onSubmit={handleSubmit}
              submitLabel="Update Recommendations"
              showValidationError={showValidationError}
            />
          </div>
        )}
      </div>

      {/* State B: loading */}
      {recsLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* State D: error */}
      {isError && !recsLoading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          {recsError && 'response' in recsError && (recsError as any).response?.status === 429 ? (
            <>
              <h3 className="text-sm font-bold text-red-800 mb-1">Too many requests</h3>
              <p className="text-sm text-red-700 mb-3">
                Please wait a moment before requesting new recommendations.
              </p>
            </>
          ) : (
            <>
              <h3 className="text-sm font-bold text-red-800 mb-1">Could not load recommendations</h3>
              <p className="text-sm text-red-700 mb-3">
                Something went wrong. Check your connection and try again.
              </p>
            </>
          )}
          <button
            type="button"
            onClick={() => refetch()}
            className="text-sm text-red-700 font-bold hover:underline"
          >
            Try Again
          </button>
        </div>
      )}

      {/* No results state */}
      {!recsLoading && !isError && recommendations.length === 0 && hasSubmitted && (
        <div className="text-center py-20">
          <p className="text-lg font-bold text-gray-900">
            No recommendations found for your preferences.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Try selecting different genres or changing your mood.
          </p>
        </div>
      )}

      {/* State C: results */}
      {!recsLoading && !isError && recommendations.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {recommendations.map((item) => (
            <div key={item.tmdb_id} className="flex flex-col">
              <MovieCard movie={toMovieSummary(item)} />
              {item.overview && (
                <p className="mt-1 text-xs text-gray-400 line-clamp-2">{item.overview}</p>
              )}
              <div className="mt-1 flex items-center gap-2">
                <p className="text-xs text-gray-500 italic flex-1">{item.explanation}</p>
                {isAuthenticated && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleVote(item.tmdb_id, 'like')}
                      className={`p-1 rounded transition-colors ${
                        votes.get(item.tmdb_id) === 'like'
                          ? 'text-green-600 bg-green-50'
                          : 'text-gray-400 hover:text-green-500'
                      }`}
                      aria-label="Like"
                      title="Like"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                        <path d="M1 8.998a1 1 0 0 1 1-1h3v9H2a1 1 0 0 1-1-1v-7Zm5.5 8.5h7.168a2 2 0 0 0 1.94-1.516l1.333-5.333A2 2 0 0 0 15 7.498H11V3.498a1.5 1.5 0 0 0-1.5-1.5.5.5 0 0 0-.462.31L6.5 8.498v9Z"/>
                      </svg>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleVote(item.tmdb_id, 'dislike')}
                      className={`p-1 rounded transition-colors ${
                        votes.get(item.tmdb_id) === 'dislike'
                          ? 'text-red-600 bg-red-50'
                          : 'text-gray-400 hover:text-red-500'
                      }`}
                      aria-label="Dislike"
                      title="Dislike"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                        <path d="M19 11.002a1 1 0 0 1-1 1h-3v-9h3a1 1 0 0 1 1 1v7Zm-5.5-8.5H6.332a2 2 0 0 0-1.94 1.516L3.06 9.351a2 2 0 0 0 1.94 2.484H9v3.5a1.5 1.5 0 0 0 1.5 1.5.5.5 0 0 0 .462-.31l2.538-6.023v-9Z"/>
                      </svg>
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RecommendationsPage;

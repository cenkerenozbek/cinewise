import { useState } from 'react';
import { isAxiosError } from 'axios';
import {
  useRecommendations,
  useSaveUserPreferences,
  useUserPreferences,
} from '../hooks/useRecommendations';
import { useGenres } from '../hooks/useMovies';
import { GenreChipGroup, MoodChipGroup } from '../components/PreferenceChips';
import { RecommendationCard } from '../components/RecommendationCard';
import { useFeedback } from '../hooks/useFeedback';
import { useAuth } from '../hooks/useAuth';
import { useMetrics } from '../hooks/useMetrics';
import type { FeedbackAction, UserPreferences } from '../lib/types';

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
  const { isAuthenticated, user } = useAuth();
  const authCacheKey = user?.id ?? 'anonymous';
  const { data: savedPrefs, isLoading: prefsLoading } = useUserPreferences(
    isAuthenticated,
    authCacheKey,
  );
  const { data: genresData } = useGenres();

  const [draftPrefs, setDraftPrefs] = useState<UserPreferences | null>(null);
  const [submittedPrefs, setSubmittedPrefs] = useState<UserPreferences | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showValidationError, setShowValidationError] = useState(false);
  const [votes, setVotes] = useState<Map<number, FeedbackAction>>(new Map());
  const { mutate: submitFeedback } = useFeedback();
  const { mutate: savePreferences, isPending: isSavingPreferences } =
    useSaveUserPreferences(authCacheKey);
  const { data: metrics } = useMetrics();

  const availableGenres = genresData ?? [];
  const savedActivePrefs = savedPrefs && savedPrefs.genres.length > 0 ? savedPrefs : null;
  const activePrefs = submittedPrefs ?? savedActivePrefs;
  const selectedGenres = draftPrefs?.genres ?? activePrefs?.genres ?? [];
  const selectedMood = draftPrefs?.mood ?? activePrefs?.mood ?? null;
  const hasSubmitted = Boolean(activePrefs);

  const {
    data: recommendationData,
    isLoading: recsLoading,
    isError,
    error: recsError,
    refetch,
  } = useRecommendations(
    activePrefs?.genres ?? [],
    activePrefs?.mood ?? null,
    authCacheKey,
  );

  function handleGenreToggle(genre: string) {
    setDraftPrefs((prev) => {
      const baseGenres = prev?.genres ?? selectedGenres;
      const nextGenres = baseGenres.includes(genre)
        ? baseGenres.filter((g) => g !== genre)
        : [...baseGenres, genre];

      return {
        genres: nextGenres,
        mood: prev?.mood ?? selectedMood,
      };
    });
    setShowValidationError(false);
  }

  function handleMoodSelect(mood: string | null) {
    setDraftPrefs((prev) => ({
      genres: prev?.genres ?? selectedGenres,
      mood,
    }));
  }

  function handleSubmit() {
    if (selectedGenres.length === 0) {
      setShowValidationError(true);
      return;
    }
    const nextPrefs = { genres: selectedGenres, mood: selectedMood };
    setShowValidationError(false);
    setSubmittedPrefs(nextPrefs);
    setDraftPrefs(nextPrefs);
    savePreferences(nextPrefs);
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
  const rateLimited = isAxiosError(recsError) && recsError.response?.status === 429;

  if (prefsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Your Recommendations</h1>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

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
            onMoodSelect={handleMoodSelect}
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

      {/* Evaluation metrics -- shown only when metrics.json was loaded */}
      {metrics && (
        <div className="mb-4 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 flex items-center gap-4">
          <span>
            <span className="font-medium text-gray-700">Precision@10:</span>{' '}
            {metrics.precision_at_10.toFixed(3)}
          </span>
          <span className="text-gray-300">|</span>
          <span>
            <span className="font-medium text-gray-700">NDCG@10:</span>{' '}
            {metrics.ndcg_at_10.toFixed(3)}
          </span>
          <span className="text-gray-300">|</span>
          <span>
            Evaluated on {metrics.n_users} users ({metrics.eval_date})
          </span>
        </div>
      )}

      {activePrefs && (
        <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          <span className="font-bold">Active preferences:</span>{' '}
          {activePrefs.genres.join(', ')}
          {activePrefs.mood ? ` / ${activePrefs.mood}` : ''}
          {isSavingPreferences && <span className="ml-2 text-blue-700">Saving...</span>}
        </div>
      )}

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
              onMoodSelect={handleMoodSelect}
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
          {rateLimited ? (
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
    </div>
  );
}

export default RecommendationsPage;

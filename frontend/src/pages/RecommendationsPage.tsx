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
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import type { FeedbackAction, UserPreferences } from '../lib/types';

function SkeletonCard() {
  return (
    <div className="rounded-xl overflow-hidden animate-pulse" style={{ background: 'var(--cw-surface)' }}>
      <div className="aspect-[2/3]" style={{ background: 'var(--cw-surface-elevated)' }} />
      <div className="p-2.5 space-y-2">
        <div className="h-3 rounded w-3/4" style={{ background: 'var(--cw-surface-elevated)' }} />
        <div className="h-2 rounded w-1/2" style={{ background: 'var(--cw-surface-elevated)' }} />
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
    <div
      className="rounded-2xl border p-6"
      style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
    >
      <div className="space-y-6">
        <div>
          <p className="text-sm font-bold text-slate-300">Select Genres</p>
          <GenreChipGroup
            genres={availableGenres}
            selected={selectedGenres}
            onToggle={onGenreToggle}
          />
          {showValidationError && (
            <p className="text-sm text-red-400 mt-1">Please select at least one genre.</p>
          )}
        </div>
        <div>
          <p className="text-sm font-bold text-slate-300">
            How are you feeling?{' '}
            <span className="text-xs text-slate-500 font-normal">(optional)</span>
          </p>
          <MoodChipGroup selected={selectedMood} onSelect={onMoodSelect} />
        </div>
      </div>
      <button
        type="button"
        onClick={onSubmit}
        disabled={selectedGenres.length === 0}
        className="mt-6 w-full py-2.5 px-4 font-bold rounded-xl disabled:opacity-50 transition-all text-white"
        style={{ background: 'var(--cw-accent)' }}
      >
        {submitLabel}
      </button>
    </div>
  );
}

export function RecommendationsPage() {
  const { isAuthenticated, user } = useAuth();
  const { setActiveMood } = useMoodTheme();
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
      return { genres: nextGenres, mood: prev?.mood ?? selectedMood };
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
    // Trigger mood-based theme change
    setActiveMood(selectedMood);
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
      }
    );
  }

  const recommendations = recommendationData?.recommendations ?? [];
  const rateLimited = isAxiosError(recsError) && recsError.response?.status === 429;

  if (prefsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-slate-100 mb-4">Your Recommendations</h1>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (!hasSubmitted && !prefsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-slate-100 mb-2">Your Recommendations</h1>
        <p className="text-slate-400 mb-6 text-sm">Tell us what you enjoy to get started.</p>
        <div className="max-w-xl">
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
      <h1 className="text-2xl font-bold text-slate-100 mb-4">Your Recommendations</h1>

      {/* Evaluation metrics */}
      {metrics && (
        <div
          className="mb-4 text-sm rounded-xl px-4 py-2.5 flex flex-wrap items-center gap-4 border"
          style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
        >
          <span>
            <span className="font-bold text-slate-300">Hit Rate@10:</span>{' '}
            <span className="text-slate-400">{metrics.precision_at_10.toFixed(3)}</span>
          </span>
          <span className="text-slate-600">|</span>
          <span>
            <span className="font-bold text-slate-300">NDCG@10:</span>{' '}
            <span className="text-slate-400">{metrics.ndcg_at_10.toFixed(3)}</span>
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-500 text-xs">
            Evaluated on {metrics.n_users} users ({metrics.eval_date})
          </span>
        </div>
      )}

      {/* Active preferences bar */}
      {activePrefs && (
        <div
          className="mb-4 rounded-xl border px-4 py-3 text-sm flex items-center gap-2 flex-wrap"
          style={{ borderColor: 'var(--cw-accent)33', background: 'var(--cw-accent)11' }}
        >
          <span className="font-bold text-slate-300">Active:</span>
          <span className="text-slate-400">{activePrefs.genres.join(', ')}</span>
          {activePrefs.mood && (
            <span
              className="px-2 py-0.5 rounded-full text-xs font-bold border"
              style={{ borderColor: 'var(--cw-accent)', color: 'var(--cw-accent)', background: 'var(--cw-accent)15' }}
            >
              {activePrefs.mood}
            </span>
          )}
          {isSavingPreferences && <span className="text-xs text-slate-500 ml-auto">Saving...</span>}
        </div>
      )}

      <div className="mb-4">
        <button
          type="button"
          onClick={() => setShowForm((prev) => !prev)}
          className="px-4 py-2 text-sm font-bold rounded-xl border transition-all"
          style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
        >
          {showForm ? 'Hide' : 'Edit Preferences'}
        </button>
        {showForm && (
          <div className="mt-4 max-w-xl">
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

      {recsLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {isError && !recsLoading && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4">
          {rateLimited ? (
            <>
              <h3 className="text-sm font-bold text-red-400 mb-1">Too many requests</h3>
              <p className="text-sm text-red-400/80 mb-3">Please wait a moment before requesting new recommendations.</p>
            </>
          ) : (
            <>
              <h3 className="text-sm font-bold text-red-400 mb-1">Could not load recommendations</h3>
              <p className="text-sm text-red-400/80 mb-3">Something went wrong. Check your connection and try again.</p>
            </>
          )}
          <button type="button" onClick={() => refetch()} className="text-sm font-bold" style={{ color: 'var(--cw-accent)' }}>
            Try Again
          </button>
        </div>
      )}

      {!recsLoading && !isError && recommendations.length === 0 && hasSubmitted && (
        <div className="text-center py-20">
          <p className="text-lg font-bold text-slate-300">No recommendations found for your preferences.</p>
          <p className="text-sm text-slate-500 mt-2">Try selecting different genres or changing your mood.</p>
        </div>
      )}

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

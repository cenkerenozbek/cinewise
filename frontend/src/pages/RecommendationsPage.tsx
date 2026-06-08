import { useState, useRef } from 'react';
import { isAxiosError } from 'axios';
import {
  useRecommendations,
  useSaveUserPreferences,
  useUserPreferences,
} from '../hooks/useRecommendations';
import { useGenres } from '../hooks/useMovies';
import { GenreChipGroup, MoodChipGroup } from '../components/PreferenceChips';
import { RecommendationCard } from '../components/RecommendationCard';
import { useFeedback, useDeleteFeedback } from '../hooks/useFeedback';
import { useAuth } from '../hooks/useAuth';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import type { FeedbackAction, UserPreferences } from '../lib/types';

const MOOD_OPTIONS = [
  { key: 'Happy',        icon: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z', color: '#f59e0b' },
  { key: 'Tense',        icon: 'M13 10V3L4 14h7v7l9-11h-7z',                                                                                                                         color: '#2dd4bf' },
  { key: 'Relaxing',     icon: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z',                                                               color: '#b8a4ed' },
  { key: 'Mind-bending', icon: 'M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z', color: '#a855f7' },
  { key: 'Romantic',     icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',                       color: '#fb7185' },
];

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

interface MoodSidebarProps {
  activeMood: string | null;
  onSelect: (mood: string | null) => void;
}

function MoodSidebar({ activeMood, onSelect }: MoodSidebarProps) {
  const [open, setOpen] = useState(true);
  const activeOption = MOOD_OPTIONS.find(m => m.key === activeMood);

  return (
    <aside
      className="hidden lg:block flex-shrink-0 transition-all duration-300"
      style={{ width: open ? '168px' : '52px' }}
    >
      <div className="sticky top-20 flex flex-col gap-2">

        {/* ── Collapsed: emoji column ── */}
        {!open && (
          <div className="flex flex-col items-center gap-2">
            {/* expand button */}
            <button
              type="button"
              onClick={() => setOpen(true)}
              title="Open mood panel"
              className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:scale-105"
              style={{ background: 'var(--cw-surface)', border: '1px solid var(--cw-border)' }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </button>
            {MOOD_OPTIONS.map(({ key, icon, color }) => {
              const active = activeMood === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => onSelect(active ? null : key)}
                  title={key}
                  className="w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-110"
                  style={
                    active
                      ? { background: color, boxShadow: `0 0 14px ${color}80` }
                      : { background: 'var(--cw-surface)', border: '1px solid var(--cw-border)' }
                  }
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke={active ? 'white' : color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d={icon} />
                  </svg>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Expanded panel ── */}
        {open && (
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'var(--cw-surface)',
              border: `1px solid ${activeOption ? activeOption.color + '50' : 'var(--cw-border)'}`,
              boxShadow: activeOption ? `0 0 24px ${activeOption.color}18` : 'none',
              transition: 'border-color 0.4s ease, box-shadow 0.4s ease',
            }}
          >
            {/* gradient accent strip */}
            <div
              className="h-0.5 w-full transition-all duration-500"
              style={{
                background: activeOption
                  ? `linear-gradient(90deg, ${activeOption.color}, transparent)`
                  : 'var(--cw-surface-elevated)',
              }}
            />

            <div className="p-3">
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-[0.15em]">
                  Mood
                </span>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  title="Collapse"
                  className="w-6 h-6 rounded-lg flex items-center justify-center text-slate-600 hover:text-slate-300 transition-colors"
                  style={{ background: 'var(--cw-surface-elevated)' }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              {/* Mood buttons */}
              <div className="flex flex-col gap-1">
                {MOOD_OPTIONS.map(({ key, icon, color }) => {
                  const active = activeMood === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => onSelect(active ? null : key)}
                      className="group relative flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-normal transition-all duration-200 text-left w-full overflow-hidden"
                      style={
                        active
                          ? {
                              background: `linear-gradient(135deg, ${color}ee, ${color}99)`,
                              color: '#fff',
                              boxShadow: `0 4px 16px ${color}50`,
                            }
                          : {
                              background: 'var(--cw-surface-elevated)',
                              color: '#64748b',
                            }
                      }
                    >
                      {/* hover shimmer */}
                      {!active && (
                        <span
                          className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"
                          style={{ background: `${color}15` }}
                        />
                      )}
                      {/* active pulse dot */}
                      {active && (
                        <span
                          className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full"
                          style={{ background: 'rgba(255,255,255,0.7)' }}
                        />
                      )}
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0 z-10" fill="none" viewBox="0 0 24 24" stroke={active ? 'white' : color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                        <path d={icon} />
                      </svg>
                      <span className="z-10">{key}</span>
                    </button>
                  );
                })}
              </div>

              {/* Clear */}
              {activeMood && (
                <button
                  type="button"
                  onClick={() => onSelect(null)}
                  className="mt-2.5 w-full text-[11px] font-medium text-slate-600 hover:text-slate-300 transition-colors text-center py-1"
                >
                  ✕ Clear
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
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
  const { activeMood, setActiveMood } = useMoodTheme();
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
  const [recommendationRevision, setRecommendationRevision] = useState(0);
  const sidebarDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { mutate: submitFeedback } = useFeedback();
  const { mutate: deleteFeedback } = useDeleteFeedback();
  const { mutate: savePreferences, isPending: isSavingPreferences } =
    useSaveUserPreferences(authCacheKey);
  // metrics intentionally not shown on the main page — internal eval data

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
    recommendationRevision,
  );

  function handleGenreToggle(genre: string) {
    const baseGenres = draftPrefs?.genres ?? selectedGenres;
    const nextGenres = baseGenres.includes(genre)
      ? baseGenres.filter((g) => g !== genre)
      : [...baseGenres, genre];
    const mood = draftPrefs?.mood ?? selectedMood;
    setDraftPrefs({ genres: nextGenres, mood });
    setShowValidationError(false);
  }

  function handleMoodSelect(mood: string | null) {
    const genres = draftPrefs?.genres ?? selectedGenres;
    setDraftPrefs({ genres, mood });
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
    setRecommendationRevision((revision) => revision + 1);
    savePreferences(nextPrefs);
    setShowForm(false);
    setActiveMood(selectedMood);
  }

  function handleSidebarMoodSelect(mood: string | null) {
    setActiveMood(mood);
    const genres = activePrefs?.genres ?? [];
    const nextPrefs = { genres, mood };
    setDraftPrefs(nextPrefs);
    // Update recs immediately (sidebar mood change is already intentional)
    if (genres.length > 0) {
      setSubmittedPrefs(nextPrefs);
      setRecommendationRevision((revision) => revision + 1);
    }
    // Debounce the backend save so rapid switching doesn't spam the API
    if (sidebarDebounceRef.current) clearTimeout(sidebarDebounceRef.current);
    sidebarDebounceRef.current = setTimeout(() => {
      if (nextPrefs.genres.length > 0) {
        setSubmittedPrefs(nextPrefs);
        savePreferences(nextPrefs);
      }
    }, 600);
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

  function handleClearVote(tmdbId: number) {
    const prev = votes.get(tmdbId);
    setVotes((m) => {
      const next = new Map(m);
      next.delete(tmdbId);
      return next;
    });
    deleteFeedback(tmdbId, {
      onError: () => {
        if (prev) setVotes((m) => new Map(m).set(tmdbId, prev));
      },
    });
  }

  const recommendations = recommendationData?.recommendations ?? [];
  const rateLimited = isAxiosError(recsError) && recsError.response?.status === 429;

  if (prefsLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-bold text-slate-100 mb-4">Your Recommendations</h1>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
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

      <div className="flex gap-12 items-start">
        {/* ── Main content ─────────────────────────── */}
        <div className="flex-1 min-w-0">
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
                  {(() => { const m = MOOD_OPTIONS.find(o => o.key === activePrefs.mood); return m ? <svg xmlns="http://www.w3.org/2000/svg" className="inline h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d={m.icon} /></svg> : null; })()} {activePrefs.mood}
                </span>
              )}
              {isSavingPreferences && <span className="text-xs text-slate-500 ml-auto">Saving...</span>}
            </div>
          )}

          {/* Edit Preferences toggle */}
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
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
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
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {recommendations.map((item) => (
                <RecommendationCard
                  key={item.tmdb_id}
                  item={item}
                  vote={votes.get(item.tmdb_id)}
                  onVote={handleVote}
                  onClearVote={handleClearVote}
                  showFeedback={isAuthenticated}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Mood sidebar ─────────────────────────── */}
        <MoodSidebar
          activeMood={activeMood}
          onSelect={handleSidebarMoodSelect}
        />
      </div>
    </div>
  );
}

export default RecommendationsPage;

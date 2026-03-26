import { useState, useEffect } from 'react';
import { useRecommendations, useUserPreferences } from '../hooks/useRecommendations';
import { useGenres } from '../hooks/useMovies';
import { MovieCard } from '../components/MovieCard';
import { GenreChipGroup, MoodChipGroup } from '../components/PreferenceChips';
import type { MovieSummary, RecommendationItem } from '../lib/types';

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

  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [submittedGenres, setSubmittedGenres] = useState<string[]>([]);
  const [submittedMood, setSubmittedMood] = useState<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [showValidationError, setShowValidationError] = useState(false);

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
          <h3 className="text-sm font-bold text-red-800 mb-1">Could not load recommendations</h3>
          <p className="text-sm text-red-700 mb-3">
            Something went wrong. Check your connection and try again.
          </p>
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
              <p className="mt-1 text-xs text-gray-500 italic">{item.explanation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RecommendationsPage;

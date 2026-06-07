import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGenres, useMovieSearch } from '../hooks/useMovies';
import { useSaveUserPreferences } from '../hooks/useRecommendations';
import { useFeedback } from '../hooks/useFeedback';
import { useAuth } from '../hooks/useAuth';
import { GenreChipGroup, MoodChipGroup } from '../components/PreferenceChips';
import { useMoodTheme } from '../features/mood/MoodThemeContext';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w300';

export function OnboardingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { setActiveMood } = useMoodTheme();
  const [step, setStep] = useState(0);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [ratedMovies, setRatedMovies] = useState<Map<number, 'like' | 'dislike'>>(new Map());

  const { data: genresData } = useGenres();
  const { data: popularMoviesData } = useMovieSearch('', '', '', 1);
  const { mutate: savePrefs } = useSaveUserPreferences(user?.id ?? 'anon');
  const { mutate: submitFeedback } = useFeedback();

  const popularMovies = (popularMoviesData?.movies ?? []).slice(0, 8);
  const availableGenres = genresData ?? [];

  function handleGenreToggle(g: string) {
    setSelectedGenres((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
    );
  }

  function handleRate(movieId: number, action: 'like' | 'dislike') {
    setRatedMovies((prev) => new Map(prev).set(movieId, action));
    submitFeedback({ movie_id: movieId, action });
  }

  function handleFinish() {
    if (selectedGenres.length > 0) {
      savePrefs({ genres: selectedGenres, mood: selectedMood });
      if (selectedMood) setActiveMood(selectedMood);
    }
    navigate('/recommendations');
  }

  const STEPS = [
    {
      title: 'What genres do you love?',
      subtitle: 'Select at least one to personalize your recommendations.',
      content: (
        <div>
          <GenreChipGroup genres={availableGenres} selected={selectedGenres} onToggle={handleGenreToggle} />
          {selectedGenres.length === 0 && (
            <p className="text-xs text-slate-500 mt-3">Select at least one genre to continue.</p>
          )}
        </div>
      ),
      canProceed: selectedGenres.length > 0,
    },
    {
      title: 'How are you feeling today?',
      subtitle: 'Optional — helps us pick the right tone.',
      content: (
        <MoodChipGroup selected={selectedMood} onSelect={setSelectedMood} />
      ),
      canProceed: true,
    },
    {
      title: 'Rate a few popular films',
      subtitle: 'This seeds your recommendation engine instantly.',
      content: (
        <div className="grid grid-cols-4 gap-3">
          {popularMovies.map((movie) => {
            const vote = ratedMovies.get(movie.tmdb_id);
            return (
              <div key={movie.tmdb_id} className="flex flex-col gap-1.5">
                <div className={`relative rounded-lg overflow-hidden aspect-[2/3] transition-all ${vote ? 'ring-2' : ''} ${vote === 'like' ? 'ring-green-400' : vote === 'dislike' ? 'ring-red-400' : ''}`} style={{ background: 'var(--cw-surface-elevated)' }}>
                  {movie.poster_path && (
                    <img src={`${TMDB_POSTER_BASE}${movie.poster_path}`} alt={movie.title} className="w-full h-full object-cover" loading="lazy" />
                  )}
                </div>
                <p className="text-xs text-slate-400 truncate text-center">{movie.title}</p>
                <div className="grid grid-cols-3 gap-1">
                  <button
                    type="button"
                    onClick={() => handleRate(movie.tmdb_id, 'like')}
                    className={`rounded py-1 text-sm transition-all ${vote === 'like' ? 'bg-green-500/30 text-green-300' : 'bg-white/5 text-slate-400 hover:text-green-300'}`}
                    title="Love it"
                  >👍</button>
                  <button
                    type="button"
                    onClick={() => {
                      setRatedMovies((prev) => {
                        const next = new Map(prev);
                        next.delete(movie.tmdb_id);
                        return next;
                      });
                    }}
                    className="rounded py-1 text-sm bg-white/5 text-slate-500 hover:text-slate-300"
                    title="Skip"
                  >—</button>
                  <button
                    type="button"
                    onClick={() => handleRate(movie.tmdb_id, 'dislike')}
                    className={`rounded py-1 text-sm transition-all ${vote === 'dislike' ? 'bg-red-500/30 text-red-300' : 'bg-white/5 text-slate-400 hover:text-red-300'}`}
                    title="Not for me"
                  >👎</button>
                </div>
              </div>
            );
          })}
        </div>
      ),
      canProceed: true,
    },
  ];

  const currentStep = STEPS[step];

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-2xl animate-fade-in-up">
        {/* Progress dots */}
        <div className="flex items-center gap-2 justify-center mb-8">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className="h-1.5 rounded-full transition-all duration-300"
              style={{
                width: i === step ? 32 : 8,
                background: i <= step ? 'var(--cw-accent)' : 'var(--cw-surface-elevated)',
              }}
            />
          ))}
        </div>

        <div
          className="rounded-2xl border p-8"
          style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
        >
          <h1 className="text-2xl font-black text-slate-100 mb-1">{currentStep.title}</h1>
          <p className="text-slate-400 text-sm mb-6">{currentStep.subtitle}</p>
          {currentStep.content}

          <div className="flex items-center justify-between mt-8">
            {step > 0 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
              >
                ← Back
              </button>
            ) : (
              <div />
            )}
            <button
              type="button"
              disabled={!currentStep.canProceed}
              onClick={() => {
                if (step < STEPS.length - 1) {
                  setStep((s) => s + 1);
                } else {
                  handleFinish();
                }
              }}
              className="px-6 py-2.5 rounded-xl font-bold text-white disabled:opacity-40 transition-all hover:opacity-90"
              style={{ background: 'var(--cw-accent)' }}
            >
              {step < STEPS.length - 1 ? 'Continue →' : "Get My Recommendations 🎬"}
            </button>
          </div>
        </div>

        <p className="text-center mt-4 text-xs text-slate-500">
          Step {step + 1} of {STEPS.length}
        </p>
      </div>
    </div>
  );
}

export default OnboardingPage;

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGenres, usePopularMovies } from '../hooks/useMovies';
import { useSaveUserPreferences } from '../hooks/useRecommendations';
import { useFeedback } from '../hooks/useFeedback';
import { useUpdateProfile } from '../hooks/useProfile';
import { useAuth } from '../hooks/useAuth';
import { GenreChipGroup, MoodChipGroup } from '../components/PreferenceChips';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import { AVATARS } from '../lib/avatars';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w300';

export function OnboardingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { setActiveMood } = useMoodTheme();

  const [step, setStep] = useState(0);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(null);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [ratedMovies, setRatedMovies] = useState<Map<number, 'like' | 'dislike'>>(new Map());

  const { data: genresData } = useGenres();
  const { data: popularMoviesData } = usePopularMovies(24);
  const { mutate: savePrefs } = useSaveUserPreferences(user?.id ?? 'anon');
  const { mutate: submitFeedback } = useFeedback();
  const { mutate: updateProfile } = useUpdateProfile();

  const popularMovies = popularMoviesData?.movies ?? [];
  const availableGenres = genresData ?? [];

  function handleGenreToggle(g: string) {
    setSelectedGenres((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
    );
  }

  function handleToggle(movieId: number) {
    setRatedMovies((prev) => {
      const next = new Map(prev);
      const current = next.get(movieId);
      if (current === 'like') {
        next.set(movieId, 'dislike');
        submitFeedback({ movie_id: movieId, action: 'dislike' });
      } else if (current === 'dislike') {
        next.delete(movieId);
      } else {
        next.set(movieId, 'like');
        submitFeedback({ movie_id: movieId, action: 'like' });
      }
      return next;
    });
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
      title: 'Welcome to Cinewise',
      subtitle: 'Tell us a bit about yourself and pick your character.',
      canProceed: true,
      onNext: () => {
        updateProfile({
          first_name: firstName.trim(),
          last_name: lastName.trim() || undefined,
          avatar_id: selectedAvatar!,
        });
      },
      content: (
        <div className="flex flex-col gap-6">
          {/* Name fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                First Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all"
                style={{ background: 'var(--cw-surface-elevated)', borderColor: 'var(--cw-border)' }}
                placeholder="Alex"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                Last Name
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all"
                style={{ background: 'var(--cw-surface-elevated)', borderColor: 'var(--cw-border)' }}
                placeholder="Smith"
              />
            </div>
          </div>

          {/* Avatar grid */}
          <div>
            <p className="text-xs font-medium text-slate-400 mb-3 uppercase tracking-widest">
              Choose your character <span className="text-red-400">*</span>
            </p>
            <div className="grid grid-cols-4 gap-3">
              {AVATARS.map((avatar) => {
                const isSelected = selectedAvatar === avatar.id;
                return (
                  <button
                    key={avatar.id}
                    type="button"
                    onClick={() => setSelectedAvatar(avatar.id)}
                    className="flex flex-col items-center gap-1.5 group"
                  >
                    <div
                      className={`w-full aspect-square rounded-xl overflow-hidden transition-all duration-200 ${
                        isSelected
                          ? 'ring-2 ring-offset-2 scale-105'
                          : 'ring-1 hover:scale-102 opacity-70 hover:opacity-100'
                      }`}
                      style={isSelected
                        ? { outline: '2px solid var(--cw-accent)', outlineOffset: '2px' }
                        : { outline: '1px solid var(--cw-border)' }
                      }
                    >
                      <img
                        src={avatar.file}
                        alt={avatar.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <span className={`text-[10px] text-center leading-tight transition-colors ${isSelected ? 'text-slate-100 font-medium' : 'text-slate-500'}`}>
                      {avatar.name}
                    </span>
                  </button>
                );
              })}
            </div>
            {selectedAvatar && (
              <p className="mt-3 text-xs text-slate-400 italic text-center animate-fade-in-up">
                "{AVATARS.find(a => a.id === selectedAvatar)?.description}"
              </p>
            )}
          </div>
        </div>
      ),
    },
    {
      title: 'What genres do you love?',
      subtitle: 'Select at least one to personalize your recommendations.',
      canProceed: true,
      onNext: undefined,
      content: (
        <div>
          <GenreChipGroup genres={availableGenres} selected={selectedGenres} onToggle={handleGenreToggle} />
          {selectedGenres.length === 0 && (
            <p className="text-xs text-slate-500 mt-3">Skip or select genres to personalize your feed.</p>
          )}
        </div>
      ),
    },
    {
      title: 'How are you feeling today?',
      subtitle: 'Optional — helps us pick the right tone.',
      canProceed: true,
      onNext: undefined,
      content: (
        <MoodChipGroup selected={selectedMood} onSelect={setSelectedMood} />
      ),
    },
    {
      title: 'Pick films you know',
      subtitle: 'Tap a film to rate it. Tap again to change. All films stay visible.',
      canProceed: true,
      onNext: undefined,
      content: (
        <div>
          <div className="flex items-center gap-4 mb-4 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> Loved it
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> Not for me
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full inline-block" style={{ background: 'var(--cw-surface-elevated)' }} /> Not seen / skip
            </span>
          </div>
          <div className="grid grid-cols-4 gap-2.5 max-h-[500px] overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
            {popularMovies.map((movie) => {
              const vote = ratedMovies.get(movie.tmdb_id);
              return (
                <button
                  key={movie.tmdb_id}
                  type="button"
                  onClick={() => handleToggle(movie.tmdb_id)}
                  className="relative rounded-lg overflow-hidden aspect-[2/3] group focus:outline-none transition-transform hover:scale-[1.02]"
                  style={{
                    background: 'var(--cw-surface-elevated)',
                    outline: vote === 'like' ? '2.5px solid #22c55e' : vote === 'dislike' ? '2.5px solid #ef4444' : '2px solid transparent',
                    outlineOffset: '1px',
                  }}
                >
                  {movie.poster_path && (
                    <img
                      src={`${TMDB_POSTER_BASE}${movie.poster_path}`}
                      alt={movie.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  )}
                  {/* dark overlay on hover */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                  {/* vote badge */}
                  {vote && (
                    <div className={`absolute top-1.5 right-1.5 w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg ${vote === 'like' ? 'bg-green-500' : 'bg-red-500'}`}>
                      {vote === 'like' ? '✓' : '✕'}
                    </div>
                  )}
                  {/* title on hover */}
                  <div className="absolute bottom-0 left-0 right-0 p-1.5 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                    <p className="text-[10px] text-white font-medium line-clamp-2 leading-tight">{movie.title}</p>
                  </div>
                </button>
              );
            })}
          </div>
          {ratedMovies.size > 0 && (
            <p className="mt-3 text-xs text-slate-400 text-center">
              {[...ratedMovies.values()].filter(v => v === 'like').length} loved · {[...ratedMovies.values()].filter(v => v === 'dislike').length} not for me
            </p>
          )}
        </div>
      ),
    },
  ];

  const currentStep = STEPS[step];

  function handleNext() {
    currentStep.onNext?.();
    if (step < STEPS.length - 1) {
      setStep((s) => s + 1);
    } else {
      handleFinish();
    }
  }

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
              onClick={handleNext}
              className="px-6 py-2.5 rounded-xl font-bold text-white disabled:opacity-40 transition-all hover:opacity-90"
              style={{ background: 'var(--cw-accent)' }}
            >
              {step < STEPS.length - 1 ? 'Continue →' : 'Get My Recommendations 🎬'}
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

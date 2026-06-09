import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGenres, useMovieSearch } from '../hooks/useMovies';
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
  const { data: popularMoviesData } = useMovieSearch('', '', '', 1);
  const { mutate: savePrefs } = useSaveUserPreferences(user?.id ?? 'anon');
  const { mutate: submitFeedback } = useFeedback();
  const { mutate: updateProfile } = useUpdateProfile();

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
                      style={{
                        ringColor: isSelected ? 'var(--cw-accent)' : 'var(--cw-border)',
                        ringOffsetColor: 'var(--cw-surface)',
                        ...(isSelected ? { outline: '2px solid var(--cw-accent)', outlineOffset: '2px' } : { outline: '1px solid var(--cw-border)' }),
                      }}
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
      title: 'Rate a few popular films',
      subtitle: 'This seeds your recommendation engine instantly.',
      canProceed: true,
      onNext: undefined,
      content: (
        <div className="grid grid-cols-4 gap-3">
          {popularMovies.map((movie) => {
            const vote = ratedMovies.get(movie.tmdb_id);
            return (
              <div key={movie.tmdb_id} className="flex flex-col gap-1.5">
                <div
                  className={`relative rounded-lg overflow-hidden aspect-[2/3] transition-all ${vote ? 'ring-2' : ''} ${vote === 'like' ? 'ring-green-400' : vote === 'dislike' ? 'ring-red-400' : ''}`}
                  style={{ background: 'var(--cw-surface-elevated)' }}
                >
                  {movie.poster_path && (
                    <img src={`${TMDB_POSTER_BASE}${movie.poster_path}`} alt={movie.title} className="w-full h-full object-cover" loading="lazy" />
                  )}
                </div>
                <p className="text-xs text-slate-400 truncate text-center">{movie.title}</p>
                <div className="grid grid-cols-3 gap-1">
                  <button
                    type="button"
                    onClick={() => handleRate(movie.tmdb_id, 'like')}
                    className={`flex items-center justify-center rounded py-1.5 transition-all ${vote === 'like' ? 'bg-green-500/30 text-green-300' : 'bg-white/5 text-slate-400 hover:text-green-300'}`}
                    title="Love it"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setRatedMovies((prev) => {
                        const next = new Map(prev);
                        next.delete(movie.tmdb_id);
                        return next;
                      });
                    }}
                    className="flex items-center justify-center rounded py-1.5 bg-white/5 text-slate-500 hover:text-slate-300 transition-all"
                    title="Skip"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 12h12" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRate(movie.tmdb_id, 'dislike')}
                    className={`flex items-center justify-center rounded py-1.5 transition-all ${vote === 'dislike' ? 'bg-red-500/30 text-red-300' : 'bg-white/5 text-slate-400 hover:text-red-300'}`}
                    title="Not for me"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          })}
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

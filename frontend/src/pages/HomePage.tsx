import { useState, useEffect, useRef, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMovieSearch, useMovieDetail, useMovieTrailer } from '../hooks/useMovies';
import { useRecommendations, useUserPreferences } from '../hooks/useRecommendations';
import { MovieCard } from '../components/MovieCard';
import { MovieGrid } from '../components/MovieGrid';
import { FilterDropdowns } from '../components/FilterDropdowns';
import { useAuth } from '../hooks/useAuth';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import type { MovieSummary } from '../lib/types';

const TMDB_BACKDROP_BASE = 'https://image.tmdb.org/t/p/w1280';
const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w780';
const HERO_COUNT = 5;
const AUTO_ADVANCE_MS = 6000;

function HeroSlide({ movie }: { movie: MovieSummary }) {
  const { data: detail } = useMovieDetail(movie.tmdb_id);
  const backdropPath = detail?.backdrop_path ?? movie.backdrop_path;
  const imageUrl = backdropPath
    ? `${TMDB_BACKDROP_BASE}${backdropPath}`
    : movie.poster_path
      ? `${TMDB_POSTER_BASE}${movie.poster_path}`
      : null;

  return (
    <>
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={movie.title}
          className="absolute inset-0 w-full h-full object-cover object-center transition-opacity duration-700"
        />
      ) : (
        <div className="absolute inset-0 bg-gray-900" />
      )}
    </>
  );
}

function HeroSection({ movies, personalized = false }: { movies: MovieSummary[]; personalized?: boolean }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const heroMovies = movies.slice(0, HERO_COUNT);
  const movie = heroMovies[activeIndex];
  const { data: activeDetail } = useMovieDetail(movie?.tmdb_id ?? 0);
  const { data: trailerData } = useMovieTrailer(movie?.tmdb_id ?? 0);
  const trailerKey = trailerData?.youtube_key ?? null;

  function resetTimer() {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setActiveIndex((i) => (i + 1) % Math.max(heroMovies.length, 1));
    }, AUTO_ADVANCE_MS);
  }

  useEffect(() => {
    if (heroMovies.length === 0) return;
    resetTimer();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [heroMovies.length]);

  function goTo(index: number) {
    setActiveIndex(index);
    resetTimer();
  }

  return (
    <div className="relative -mt-16 h-[600px] overflow-hidden">
      {/* Slides */}
      {heroMovies.map((m, i) => (
        <div
          key={m.tmdb_id}
          className="absolute inset-0 transition-opacity duration-700"
          style={{ opacity: i === activeIndex ? 1 : 0, pointerEvents: i === activeIndex ? 'auto' : 'none' }}
        >
          <HeroSlide movie={m} />
        </div>
      ))}

      {/* Overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

      {/* Bottom fade into page background */}
      <div
        className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
        style={{ background: 'linear-gradient(to bottom, transparent, var(--cw-bg))' }}
      />

      {/* Content */}
      <div className="absolute bottom-16 left-[98px] max-w-[420px]">
        {movie ? (
          <>
            {personalized && (
              <div className="inline-flex items-center gap-1.5 mb-3 px-3 py-1 rounded-full text-xs font-semibold" style={{ background: 'var(--cw-accent)', color: '#fff', opacity: 0.92 }}>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                For You
              </div>
            )}
            <Link to={`/movie/${movie.tmdb_id}`}>
              <h1 className="text-5xl font-black leading-tight mb-5 transition-all duration-500 hover:underline underline-offset-4 decoration-2" style={{ color: '#ffffff' }}>
                {movie.title}
              </h1>
            </Link>
            {movie.rating !== null && (
              <div className="flex items-center gap-3 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-amber-400" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                <span className="text-sm font-bold" style={{ color: '#ffffff' }}>
                  {movie.rating.toFixed(1)}
                  <span className="font-normal text-xs ml-1" style={{ color: 'rgba(255,255,255,0.6)' }}>/10 · TMDB</span>
                </span>
              </div>
            )}
            {movie.genres && movie.genres.length > 0 && (
              <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.75)' }}>
                {movie.genres.join(' · ')}
              </p>
            )}
            {activeDetail?.overview && (
              <p className="text-sm leading-relaxed mb-5 line-clamp-3" style={{ color: 'rgba(255,255,255,0.7)' }}>
                {activeDetail.overview}
              </p>
            )}
            {trailerKey ? (
              <a
                href={`https://www.youtube.com/watch?v=${trailerKey}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold text-white transition-opacity hover:opacity-90"
                style={{ background: 'var(--cw-accent)' }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
                Watch Trailer
              </a>
            ) : (
              <Link
                to={`/movie/${movie.tmdb_id}`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold text-white transition-opacity hover:opacity-90"
                style={{ background: 'var(--cw-accent)' }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                More Info
              </Link>
            )}
          </>
        ) : (
          <div className="space-y-4">
            <div className="h-12 w-80 rounded-lg bg-white/20 animate-pulse" />
            <div className="h-4 w-48 rounded bg-white/20 animate-pulse" />
          </div>
        )}
      </div>

      {/* Pagination — clickable */}
      {heroMovies.length > 0 && (
        <div className="absolute right-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-3">
          {heroMovies.map((_, i) => (
            <button
              key={i}
              onClick={() => goTo(i)}
              className="font-bold transition-all duration-200 hover:opacity-100 focus:outline-none"
              style={{
                color: i === activeIndex ? '#ffffff' : 'rgba(255,255,255,0.35)',
                fontSize: i === activeIndex ? '15px' : '11px',
                lineHeight: 1,
              }}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SectionTitle({ title, linkTo }: { title: string; linkTo?: string }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h2 className="text-3xl font-black text-slate-100">{title}</h2>
      {linkTo && (
        <Link to={linkTo} className="flex items-center gap-1 text-base font-medium hover:opacity-70 transition-opacity" style={{ color: 'var(--cw-accent)' }}>
          See more
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      )}
    </div>
  );
}

function MovieRow({ movies, loading }: { movies: MovieSummary[]; loading?: boolean }) {
  const rowRef = useRef<HTMLDivElement>(null);

  function scroll(dir: 'left' | 'right') {
    if (rowRef.current) {
      rowRef.current.scrollBy({ left: dir === 'right' ? 280 : -280, behavior: 'smooth' });
    }
  }

  return (
    <div className="relative">
      {/* Left arrow */}
      <button
        onClick={() => scroll('left')}
        className="absolute -left-5 top-[160px] -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
        style={{ background: 'rgba(255,255,255,0.12)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.2)' }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{ color: 'var(--cw-text)' }}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Cards */}
      <div
        ref={rowRef}
        className="flex gap-8 overflow-x-auto pb-4 scrollbar-hide"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="shrink-0 w-[220px]">
                <div className="w-[220px] h-[320px] rounded-xl animate-pulse" style={{ background: 'var(--cw-surface-elevated)' }} />
                <div className="mt-3 h-3 w-24 rounded animate-pulse" style={{ background: 'var(--cw-surface-elevated)' }} />
                <div className="mt-2 h-4 w-40 rounded animate-pulse" style={{ background: 'var(--cw-surface-elevated)' }} />
              </div>
            ))
          : movies.map((movie) => (
              <MovieCard key={movie.tmdb_id} movie={movie} variant="row" />
            ))}
      </div>

      {/* Right arrow */}
      <button
        onClick={() => scroll('right')}
        className="absolute -right-5 top-[160px] -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
        style={{ background: 'rgba(255,255,255,0.12)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.2)' }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{ color: 'var(--cw-text)' }}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-16 py-10 border-t" style={{ borderColor: 'var(--cw-border)' }}>
      <div className="flex flex-col items-center gap-5">
        <p className="text-sm text-slate-400">
          © 2026 Cinewise — AI-Powered Movie Recommendations
        </p>
      </div>
    </footer>
  );
}

export function HomePage() {
  const { isAuthenticated, user } = useAuth();
  const { setActiveMood, activeMood, isDark } = useMoodTheme();
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';
  const [genre, setGenre] = useState('');
  const [year, setYear] = useState('');
  const [page, setPage] = useState(1);
  const { data, isLoading } = useMovieSearch(query, genre, year, page);
  const { data: savedPrefs, isLoading: prefsLoading } = useUserPreferences(
    isAuthenticated,
    user?.id ?? 'anonymous',
  );
  const movies = data?.movies ?? [];
  const total = data?.total ?? 0;
  const pageSize = data?.page_size ?? 20;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const isSearching = !!query || !!genre || !!year;
  const hasSavedPreferences = Boolean(savedPrefs && savedPrefs.genres.length > 0);
  const shouldShowPersonalized = isAuthenticated && hasSavedPreferences && !isSearching;

  useEffect(() => {
    if (savedPrefs?.mood) {
      setActiveMood(savedPrefs.mood);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedPrefs?.mood]);

  const {
    data: personalizedData,
    isLoading: personalizedLoading,
  } = useRecommendations(
    shouldShowPersonalized ? savedPrefs?.genres ?? [] : [],
    shouldShowPersonalized ? activeMood : null,
    user?.id ?? 'anonymous',
  );

  const personalizedRecommendations = personalizedData?.recommendations ?? [];

  useEffect(() => { setPage(1); }, [query]);

  function handleGenreChange(value: string) { setGenre(value); setPage(1); }
  function handleYearChange(value: string) { setYear(value); setPage(1); }

  // All derived values — must live before any early return to respect Rules of Hooks
  const recMovies: MovieSummary[] = personalizedRecommendations.map((r) => ({
    tmdb_id: r.tmdb_id,
    title: r.title,
    title_tr: r.title_tr,
    year: r.year,
    genres: r.genres,
    poster_path: r.poster_path,
    backdrop_path: r.backdrop_path,
    rating: r.rating,
  }));
  const usePersonalizedHero = shouldShowPersonalized && recMovies.length >= HERO_COUNT;
  const shuffledRecMovies = useMemo(() => {
    if (!usePersonalizedHero) return recMovies;
    const pool = recMovies.slice(0, Math.min(recMovies.length, 10));
    const shuffled = [...pool];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usePersonalizedHero, recMovies.length]);
  const heroMovies = usePersonalizedHero ? shuffledRecMovies.slice(0, HERO_COUNT) : movies.slice(0, HERO_COUNT);
  const forYouRowMovies = usePersonalizedHero ? recMovies.slice(HERO_COUNT) : recMovies;
  const featuredMovies = movies.slice(HERO_COUNT, HERO_COUNT + 8);
  const newArrivals = movies.slice(HERO_COUNT + 8, HERO_COUNT + 16);
  const bgColor = isDark ? 'var(--cw-bg)' : '#ffffff';

  // Search / filter mode → show grid view
  if (isSearching) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-6" style={{ background: 'var(--cw-bg)' }}>
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <FilterDropdowns genre={genre} year={year} onGenreChange={handleGenreChange} onYearChange={handleYearChange} />
        </div>
        <h2 className="text-xl font-bold mb-4" style={{ color: isDark ? '#f1f5f9' : '#111827' }}>
          Search Results
          {total > 0 && <span className="text-sm font-normal ml-2" style={{ color: isDark ? 'rgba(255,255,255,0.5)' : '#6b7280' }}>({total} movies)</span>}
        </h2>
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
            <span className="text-sm" style={{ color: isDark ? 'rgba(255,255,255,0.5)' : '#6b7280' }}>Page {page} of {totalPages}</span>
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
    );
  }

  return (
    <div style={{ background: bgColor }}>
      {/* Hero */}
      <HeroSection movies={heroMovies} personalized={usePersonalizedHero} />

      {/* Main content */}
      <div className="max-w-[1400px] mx-auto px-[98px] py-16">

        {/* For You — personalized recommendations */}
        {isAuthenticated && !prefsLoading && !hasSavedPreferences && (
          <div
            className="mb-10 flex flex-col gap-3 rounded-xl border px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
            style={{ borderColor: 'var(--cw-accent)', background: isDark ? 'var(--cw-surface)' : '#fff1f2' }}
          >
            <p className="text-sm font-medium" style={{ color: isDark ? '#f1f5f9' : '#111827' }}>
              Set your preferences to get personalized recommendations.
            </p>
            <Link
              to="/recommendations"
              className="inline-flex h-9 items-center justify-center rounded-lg px-4 text-sm font-bold text-white transition-opacity hover:opacity-90 shrink-0"
              style={{ background: 'var(--cw-accent)' }}
            >
              Set Preferences
            </Link>
          </div>
        )}

        {shouldShowPersonalized && (
          <section className="mb-14">
            <SectionTitle title={usePersonalizedHero ? "More For You" : "For You"} linkTo="/recommendations" />
            {personalizedLoading ? (
              <MovieRow movies={[]} loading />
            ) : forYouRowMovies.length > 0 ? (
              <MovieRow movies={forYouRowMovies} />
            ) : null}
          </section>
        )}

        {/* Featured Movie */}
        {featuredMovies.length > 0 && (
          <section className="mb-14">
            <SectionTitle title="Featured Movie" />
            <MovieRow movies={featuredMovies} loading={isLoading} />
          </section>
        )}

        {/* New Arrivals */}
        {newArrivals.length > 0 && (
          <section className="mb-14">
            <SectionTitle title="New Arrivals" />
            <MovieRow movies={newArrivals} loading={isLoading} />
          </section>
        )}

        {/* Browse All — for unauthenticated users */}
        {!isAuthenticated && (
          <section className="mb-14">
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
              <FilterDropdowns genre={genre} year={year} onGenreChange={handleGenreChange} onYearChange={handleYearChange} />
            </div>
          </section>
        )}
      </div>

      <Footer />
    </div>
  );
}

export default HomePage;

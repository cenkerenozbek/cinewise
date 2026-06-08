import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMovieDetail, useMovieTrailer } from '../hooks/useMovies';
import { FeedbackControls } from '../components/FeedbackControls';
import { WatchlistButton } from '../components/WatchlistButton';
import { useAuth } from '../hooks/useAuth';
import { useFeedback, useDeleteFeedback } from '../hooks/useFeedback';
import type { FeedbackAction, WatchCompletion } from '../lib/types';
import { WATCH_COMPLETION_VALUES } from '../lib/types';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500';
const TMDB_BACKDROP_BASE = 'https://image.tmdb.org/t/p/w1280';

export function MovieDetailPage() {
  const { tmdbId } = useParams<{ tmdbId: string }>();
  const { data: movie, isLoading, isError } = useMovieDetail(Number(tmdbId));
  const { data: trailerData } = useMovieTrailer(Number(tmdbId));
  const trailerKey = trailerData?.youtube_key ?? null;
  const { isAuthenticated } = useAuth();
  const { mutate: submitFeedback, isPending: feedbackPending } = useFeedback();
  const { mutate: deleteFeedback } = useDeleteFeedback();
  const [vote, setVote] = useState<FeedbackAction | undefined>();
  const [watchCompletion, setWatchCompletion] = useState<WatchCompletion | null>(null);

  function handleVote(action: FeedbackAction) {
    if (!movie) return;
    const prev = vote;
    setVote(action);
    submitFeedback(
      { movie_id: movie.tmdb_id, action },
      { onError: () => setVote(prev) },
    );
  }

  function handleClearVote() {
    if (!movie) return;
    const prev = vote;
    setVote(undefined);
    setWatchCompletion(null);
    deleteFeedback(movie.tmdb_id, { onError: () => setVote(prev) });
  }

  function handleWatchCompletion(v: WatchCompletion) {
    if (!movie) return;
    setWatchCompletion(v);
    submitFeedback({
      movie_id: movie.tmdb_id,
      action: vote ?? 'like',
      watch_completion: WATCH_COMPLETION_VALUES[v],
    });
  }

  if (isLoading) {
    return (
      <div>
        <div className="h-[340px] animate-pulse" style={{ background: 'var(--cw-surface)' }} />
        <div className="max-w-5xl mx-auto px-6 -mt-24 relative z-10">
          <div className="flex gap-8">
            <div className="w-48 h-72 rounded-2xl flex-shrink-0 animate-pulse" style={{ background: 'var(--cw-surface-elevated)' }} />
            <div className="flex-1 space-y-4 pt-28">
              <div className="h-8 rounded w-3/4 animate-pulse" style={{ background: 'var(--cw-surface)' }} />
              <div className="h-4 rounded w-1/4 animate-pulse" style={{ background: 'var(--cw-surface)' }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !movie) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <p className="text-xl text-slate-400">Movie not found</p>
        <Link to="/" className="mt-4 inline-block font-medium hover:underline" style={{ color: 'var(--cw-accent)' }}>
          Back to home
        </Link>
      </div>
    );
  }

  const posterUrl = movie.poster_path ? `${TMDB_POSTER_BASE}${movie.poster_path}` : null;
  const backdropUrl = movie.backdrop_path ? `${TMDB_BACKDROP_BASE}${movie.backdrop_path}` : null;

  return (
    <div style={{ background: 'var(--cw-bg)', minHeight: '100vh' }}>

      {/* ── Backdrop hero ── */}
      <div className="relative h-[340px] overflow-hidden">
        {backdropUrl ? (
          <img
            src={backdropUrl}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-center scale-105"
            style={{ filter: 'blur(3px)' }}
          />
        ) : (
          <div className="absolute inset-0" style={{ background: 'var(--cw-surface)' }} />
        )}
        {/* dark overlay + bottom fade */}
        <div className="absolute inset-0 bg-black/55" />
        <div className="absolute inset-0 bg-gradient-to-t from-[var(--cw-bg)] via-transparent to-transparent" />

        {/* back button */}
        <div className="absolute top-[24px] left-6">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-white/80 hover:text-white transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </Link>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="max-w-5xl mx-auto px-6 -mt-72 relative z-10 pb-16">
        <div className="flex flex-col md:flex-row gap-8 items-start">

          {/* Poster */}
          <div className="flex-shrink-0">
            {posterUrl ? (
              <img
                src={posterUrl}
                alt={movie.title}
                className="w-44 md:w-52 rounded-2xl shadow-2xl ring-1 ring-white/10"
              />
            ) : (
              <div
                className="w-44 md:w-52 aspect-[2/3] rounded-2xl flex items-center justify-center"
                style={{ background: 'var(--cw-surface)' }}
              >
                <span className="text-sm text-slate-600">No poster</span>
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 pt-20">
            <div className="flex items-start gap-3">
              <h1 className="text-3xl font-bold text-slate-100 flex-1 leading-snug">{movie.title}</h1>
              <WatchlistButton movieId={movie.tmdb_id} size="md" className="mt-1 flex-shrink-0" />
            </div>

            {movie.title_tr && movie.title_tr !== movie.title && (
              <p className="text-base text-slate-500 mt-1 italic">{movie.title_tr}</p>
            )}

            <div className="flex flex-wrap items-center gap-3 mt-3">
              {movie.year && (
                <span className="text-slate-400 text-sm">{movie.year}</span>
              )}
              {movie.rating !== null && (
                <span className="inline-flex items-center gap-1 bg-amber-400/20 text-amber-300 text-sm font-semibold px-2.5 py-0.5 rounded-full border border-amber-400/30">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {movie.rating.toFixed(1)}
                </span>
              )}
            </div>

            {movie.genres.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {movie.genres.map((g) => (
                  <span
                    key={g}
                    className="px-3 py-1 text-xs font-medium rounded-full border"
                    style={{ borderColor: 'var(--cw-accent)50', color: 'var(--cw-accent)', background: 'var(--cw-accent)15' }}
                  >
                    {g}
                  </span>
                ))}
              </div>
            )}

            {movie.overview && (
              <p className="text-sm leading-relaxed mt-4 text-slate-400 max-w-xl">
                {movie.overview}
              </p>
            )}

            {movie.director && (
              <div className="mt-4">
                <span className="text-sm font-medium text-slate-500">Director: </span>
                <span className="text-sm text-slate-300">{movie.director}</span>
              </div>
            )}
            {movie.cast && movie.cast.length > 0 && (
              <div className="mt-1.5">
                <span className="text-sm font-medium text-slate-500">Cast: </span>
                <span className="text-sm text-slate-400">{movie.cast.slice(0, 8).join(', ')}</span>
              </div>
            )}

            {/* Watch Trailer button */}
            {trailerKey && (
              <a
                href={`https://www.youtube.com/watch?v=${trailerKey}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-opacity hover:opacity-90"
                style={{ background: 'var(--cw-accent)' }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
                Watch Trailer
              </a>
            )}
          </div>
        </div>


        {/* ── Feedback ── */}
        <div className="mt-8 max-w-sm">
          {isAuthenticated ? (
            <>
              <FeedbackControls
                title={movie.title}
                vote={vote}
                onVote={handleVote}
                onClearVote={handleClearVote}
                watchCompletion={watchCompletion}
                onWatchCompletion={handleWatchCompletion}
              />
              <p className="mt-2 text-xs text-slate-500">
                {feedbackPending ? 'Saving...' : 'Your feedback trains your For You recommendations.'}
              </p>
            </>
          ) : (
            <div
              className="rounded-xl border p-4"
              style={{ borderColor: 'var(--cw-accent)33', background: 'var(--cw-accent)11' }}
            >
              <p className="text-sm font-medium text-slate-300">
                Sign in to rate movies and improve your recommendations.
              </p>
              <Link
                to="/login"
                className="mt-3 inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium text-white transition-opacity hover:opacity-90"
                style={{ background: 'var(--cw-accent)' }}
              >
                Sign In
              </Link>
            </div>
          )}
        </div>

        {(movie.vote_count !== null || movie.popularity !== null) && (
          <div className="mt-4 flex gap-4 text-xs text-slate-600">
            {movie.vote_count !== null && (
              <span>{movie.vote_count.toLocaleString()} votes</span>
            )}
            {movie.popularity !== null && (
              <span>Popularity: {movie.popularity.toFixed(1)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default MovieDetailPage;

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMovieDetail } from '../hooks/useMovies';
import { FeedbackControls } from '../components/FeedbackControls';
import { WatchlistButton } from '../components/WatchlistButton';
import { useAuth } from '../hooks/useAuth';
import { useFeedback } from '../hooks/useFeedback';
import type { FeedbackAction, WatchCompletion } from '../lib/types';
import { WATCH_COMPLETION_VALUES } from '../lib/types';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500';

export function MovieDetailPage() {
  const { tmdbId } = useParams<{ tmdbId: string }>();
  const { data: movie, isLoading, isError } = useMovieDetail(Number(tmdbId));
  const { isAuthenticated } = useAuth();
  const { mutate: submitFeedback, isPending: feedbackPending } = useFeedback();
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
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row gap-8 animate-pulse">
          <div className="w-full md:w-64 flex-shrink-0">
            <div className="aspect-[2/3] rounded-2xl" style={{ background: 'var(--cw-surface)' }} />
          </div>
          <div className="flex-1 space-y-4">
            <div className="h-8 rounded w-3/4" style={{ background: 'var(--cw-surface)' }} />
            <div className="h-4 rounded w-1/4" style={{ background: 'var(--cw-surface)' }} />
            <div className="h-4 rounded w-1/2" style={{ background: 'var(--cw-surface)' }} />
            <div className="h-24 rounded" style={{ background: 'var(--cw-surface)' }} />
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

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <Link
        to="/"
        className="inline-flex items-center hover:underline mb-6 text-sm font-medium"
        style={{ color: 'var(--cw-accent)' }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to movies
      </Link>
      <div className="flex flex-col md:flex-row gap-8">
        {/* Poster */}
        <div className="w-full md:w-64 flex-shrink-0">
          {posterUrl ? (
            <img src={posterUrl} alt={movie.title} className="w-full rounded-2xl shadow-2xl" />
          ) : (
            <div
              className="aspect-[2/3] rounded-2xl flex items-center justify-center text-slate-600"
              style={{ background: 'var(--cw-surface)' }}
            >
              <span className="text-sm">No poster</span>
            </div>
          )}
        </div>
        {/* Info */}
        <div className="flex-1">
          <div className="flex items-start gap-3">
            <h1 className="text-3xl font-bold text-slate-100 flex-1">{movie.title}</h1>
            <WatchlistButton movieId={movie.tmdb_id} size="md" className="mt-1 flex-shrink-0" />
          </div>
          {movie.title_tr && movie.title_tr !== movie.title && (
            <p className="text-lg text-slate-500 mt-1 italic">{movie.title_tr}</p>
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
          {movie.director && (
            <div className="mt-4">
              <span className="text-sm font-semibold text-slate-400">Director: </span>
              <span className="text-sm text-slate-300">{movie.director}</span>
            </div>
          )}
          {movie.cast && movie.cast.length > 0 && (
            <div className="mt-2">
              <span className="text-sm font-semibold text-slate-400">Cast: </span>
              <span className="text-sm text-slate-300">{movie.cast.slice(0, 10).join(', ')}</span>
            </div>
          )}
          {movie.overview && (
            <div className="mt-5">
              <h2 className="text-base font-semibold text-slate-300 mb-2">Overview</h2>
              <p className="text-sm text-slate-400 leading-relaxed">{movie.overview}</p>
            </div>
          )}
          <div className="mt-6 max-w-sm">
            {isAuthenticated ? (
              <>
                <FeedbackControls
                  title={movie.title}
                  vote={vote}
                  onVote={handleVote}
                  watchCompletion={watchCompletion}
                  onWatchCompletion={handleWatchCompletion}
                />
                <p className="mt-2 text-xs text-slate-500">
                  {feedbackPending
                    ? 'Saving feedback...'
                    : 'Your feedback trains your For You recommendations.'}
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
                  className="mt-3 inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-bold text-white transition-opacity hover:opacity-90"
                  style={{ background: 'var(--cw-accent)' }}
                >
                  Sign In
                </Link>
              </div>
            )}
          </div>
          {(movie.vote_count !== null || movie.popularity !== null) && (
            <div className="mt-4 flex gap-4 text-xs text-slate-500">
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
    </div>
  );
}

export default MovieDetailPage;

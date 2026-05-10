import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMovieDetail } from '../hooks/useMovies';
import { FeedbackControls } from '../components/FeedbackControls';
import { useAuth } from '../hooks/useAuth';
import { useFeedback } from '../hooks/useFeedback';
import type { FeedbackAction } from '../lib/types';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500';

export function MovieDetailPage() {
  const { tmdbId } = useParams<{ tmdbId: string }>();
  const { data: movie, isLoading, isError } = useMovieDetail(Number(tmdbId));
  const { isAuthenticated } = useAuth();
  const { mutate: submitFeedback, isPending: feedbackPending } = useFeedback();
  const [vote, setVote] = useState<FeedbackAction | undefined>();

  function handleVote(action: FeedbackAction) {
    if (!movie) return;
    const prev = vote;
    setVote(action);
    submitFeedback(
      { movie_id: movie.tmdb_id, action },
      {
        onError: () => setVote(prev),
      },
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row gap-8 animate-pulse">
          <div className="w-full md:w-64 flex-shrink-0">
            <div className="aspect-[2/3] bg-gray-300 rounded-lg" />
          </div>
          <div className="flex-1 space-y-4">
            <div className="h-8 bg-gray-300 rounded w-3/4" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
            <div className="h-24 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !movie) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <p className="text-xl text-gray-700">Movie not found</p>
        <Link to="/" className="mt-4 inline-block text-blue-600 hover:underline">
          Back to home
        </Link>
      </div>
    );
  }

  const posterUrl = movie.poster_path ? `${TMDB_POSTER_BASE}${movie.poster_path}` : null;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <Link to="/" className="inline-flex items-center text-blue-600 hover:underline mb-6 text-sm">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 mr-1"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to movies
      </Link>
      <div className="flex flex-col md:flex-row gap-8">
        {/* Poster */}
        <div className="w-full md:w-64 flex-shrink-0">
          {posterUrl ? (
            <img
              src={posterUrl}
              alt={movie.title}
              className="w-full rounded-lg shadow-lg"
            />
          ) : (
            <div className="aspect-[2/3] bg-gray-200 rounded-lg flex items-center justify-center text-gray-400">
              <span className="text-sm">No poster</span>
            </div>
          )}
        </div>
        {/* Info */}
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-gray-900">{movie.title}</h1>
          {movie.title_tr && movie.title_tr !== movie.title && (
            <p className="text-lg text-gray-500 mt-1 italic">{movie.title_tr}</p>
          )}
          <div className="flex flex-wrap items-center gap-3 mt-3">
            {movie.year && (
              <span className="text-gray-600 text-sm">{movie.year}</span>
            )}
            {movie.rating !== null && (
              <span className="inline-flex items-center gap-1 bg-yellow-100 text-yellow-800 text-sm font-semibold px-2.5 py-0.5 rounded-full">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4 text-yellow-500"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                {movie.rating.toFixed(1)}
              </span>
            )}
          </div>
          {/* Genres */}
          {movie.genres.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {movie.genres.map((g) => (
                <span
                  key={g}
                  className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full"
                >
                  {g}
                </span>
              ))}
            </div>
          )}
          {/* Director */}
          {movie.director && (
            <div className="mt-4">
              <span className="text-sm font-semibold text-gray-700">Director: </span>
              <span className="text-sm text-gray-600">{movie.director}</span>
            </div>
          )}
          {/* Cast */}
          {movie.cast && movie.cast.length > 0 && (
            <div className="mt-3">
              <span className="text-sm font-semibold text-gray-700">Cast: </span>
              <span className="text-sm text-gray-600">{movie.cast.slice(0, 10).join(', ')}</span>
            </div>
          )}
          {/* Overview */}
          {movie.overview && (
            <div className="mt-5">
              <h2 className="text-base font-semibold text-gray-900 mb-2">Overview</h2>
              <p className="text-sm text-gray-700 leading-relaxed">{movie.overview}</p>
            </div>
          )}
          <div className="mt-5 max-w-sm">
            {isAuthenticated ? (
              <>
                <FeedbackControls title={movie.title} vote={vote} onVote={handleVote} />
                <p className="mt-2 text-xs text-gray-500">
                  {feedbackPending
                    ? 'Saving feedback...'
                    : 'Your feedback updates For You recommendations.'}
                </p>
              </>
            ) : (
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                <p className="text-sm font-medium text-blue-900">
                  Sign in to like or dislike movies and improve your recommendations.
                </p>
                <Link
                  to="/login"
                  className="mt-3 inline-flex h-10 items-center justify-center rounded-md bg-blue-600 px-4 text-sm font-bold text-white hover:bg-blue-700"
                >
                  Sign In
                </Link>
              </div>
            )}
          </div>
          {/* Additional stats */}
          {(movie.vote_count !== null || movie.popularity !== null) && (
            <div className="mt-4 flex gap-4 text-xs text-gray-500">
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

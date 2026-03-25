import { Link } from 'react-router-dom';
import type { MovieSummary } from '../lib/types';

interface MovieCardProps {
  movie: MovieSummary;
  onClick?: () => void;
}

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w300';

export function MovieCard({ movie, onClick }: MovieCardProps) {
  const posterUrl = movie.poster_path
    ? `${TMDB_IMAGE_BASE}${movie.poster_path}`
    : null;

  const content = (
    <div className="rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden bg-white cursor-pointer group">
      <div className="relative aspect-[2/3] bg-gray-200 overflow-hidden">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={movie.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-16 w-16"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
              />
            </svg>
          </div>
        )}
        {movie.rating !== null && (
          <div className="absolute top-2 right-2 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-0.5 rounded-full shadow">
            {movie.rating.toFixed(1)}
          </div>
        )}
      </div>
      <div className="p-2">
        <p className="text-sm font-semibold text-gray-900 truncate">{movie.title}</p>
        {movie.year && (
          <p className="text-xs text-gray-500">{movie.year}</p>
        )}
      </div>
    </div>
  );

  if (onClick) {
    return <div onClick={onClick}>{content}</div>;
  }

  return <Link to={`/movie/${movie.tmdb_id}`}>{content}</Link>;
}

export default MovieCard;

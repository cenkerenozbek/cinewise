import { Link } from 'react-router-dom';
import type { MovieSummary } from '../lib/types';

interface MovieCardProps {
  movie: MovieSummary;
  onClick?: () => void;
  actionSlot?: React.ReactNode;
}

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w300';

export function MovieCard({ movie, onClick, actionSlot }: MovieCardProps) {
  const posterUrl = movie.poster_path
    ? `${TMDB_IMAGE_BASE}${movie.poster_path}`
    : null;

  const content = (
    <div
      className="rounded-xl overflow-hidden cursor-pointer group transition-all duration-300"
      style={{ background: 'var(--cw-surface)' }}
    >
      <div className="relative aspect-[2/3] overflow-hidden" style={{ background: 'var(--cw-surface-elevated)' }}>
        {posterUrl ? (
          <>
            <img
              src={posterUrl}
              alt={movie.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-600">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-14 w-14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
          </div>
        )}
        {movie.rating !== null && (
          <div className="absolute top-2 right-2 bg-amber-400 text-amber-900 text-xs font-bold px-2 py-0.5 rounded-full shadow">
            ★ {movie.rating.toFixed(1)}
          </div>
        )}
        {actionSlot && (
          <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            {actionSlot}
          </div>
        )}
      </div>
      <div className="p-2.5">
        <p className="text-sm font-semibold text-slate-100 truncate">{movie.title}</p>
        <div className="flex items-center justify-between mt-1">
          {movie.year && (
            <p className="text-xs text-slate-400">{movie.year}</p>
          )}
          {movie.genres && movie.genres.length > 0 && (
            <div className="flex gap-1 overflow-hidden">
              {movie.genres.slice(0, 2).map((g) => (
                <span
                  key={g}
                  className="text-[10px] px-1.5 py-0.5 rounded-full font-medium truncate"
                  style={{ background: 'var(--cw-surface-elevated)', color: 'var(--cw-accent)' }}
                >
                  {g}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (onClick) {
    return <div onClick={onClick}>{content}</div>;
  }

  return <Link to={`/movie/${movie.tmdb_id}`}>{content}</Link>;
}

export default MovieCard;

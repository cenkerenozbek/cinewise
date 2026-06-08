import { Link } from 'react-router-dom';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import type { MovieSummary } from '../lib/types';

interface MovieCardProps {
  movie: MovieSummary;
  onClick?: () => void;
  actionSlot?: React.ReactNode;
  variant?: 'grid' | 'row';
}

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

export function MovieCard({ movie, onClick, actionSlot, variant = 'grid' }: MovieCardProps) {
  const { isDark } = useMoodTheme();
  const posterUrl = movie.poster_path
    ? `${TMDB_IMAGE_BASE}${movie.poster_path}`
    : null;

  if (variant === 'row') {
    const content = (
      <div className="flex flex-col gap-3 cursor-pointer group shrink-0 w-[220px]">
        {/* Poster */}
        <div className="relative w-[220px] h-[320px] rounded-xl overflow-hidden" style={{ background: 'var(--cw-surface-elevated)' }}>
          {posterUrl ? (
            <img
              src={posterUrl}
              alt={movie.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center" style={{ color: 'var(--cw-accent)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
              </svg>
            </div>
          )}
          {/* Favorite button */}
          <div className="absolute top-3 right-3">
            <div className="w-8 h-8 rounded-full bg-white/80 backdrop-blur-sm flex items-center justify-center shadow">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
          </div>
          {actionSlot && (
            <div className="absolute bottom-3 left-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              {actionSlot}
            </div>
          )}
        </div>

        {/* Info */}
        <p className="text-xs font-bold text-slate-400">
          {movie.year ?? '—'}
        </p>
        <p className="text-base font-bold leading-snug w-[220px] line-clamp-2 text-slate-100">
          {movie.title}
        </p>

        {/* Ratings row */}
        {movie.rating !== null && (
          <div className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-amber-400" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
            <span className="text-xs font-bold text-slate-100">
              {movie.rating.toFixed(1)}
            </span>
            <span className="text-[10px] text-slate-400">/10</span>
          </div>
        )}

        {/* Genres */}
        {movie.genres && movie.genres.length > 0 && (
          <p className="text-xs font-bold truncate text-slate-400">
            {movie.genres.slice(0, 3).join(', ')}
          </p>
        )}
      </div>
    );

    if (onClick) return <div onClick={onClick}>{content}</div>;
    return <Link to={`/movie/${movie.tmdb_id}`}>{content}</Link>;
  }

  // Grid variant (original design)
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
          <div className="w-full h-full flex items-center justify-center" style={{ color: isDark ? '#6b7280' : '#9ca3af' }}>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-14 w-14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
          </div>
        )}
        {movie.rating !== null && (
          <div className="absolute top-2 right-2 bg-amber-400 text-amber-900 text-xs font-bold px-2 py-0.5 rounded-full shadow">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 inline mr-0.5" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>{movie.rating.toFixed(1)}
          </div>
        )}
        {actionSlot && (
          <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            {actionSlot}
          </div>
        )}
      </div>
      <div className="p-2.5">
        <p className="text-sm font-semibold truncate text-slate-100">{movie.title}</p>
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

  if (onClick) return <div onClick={onClick}>{content}</div>;
  return <Link to={`/movie/${movie.tmdb_id}`}>{content}</Link>;
}

export default MovieCard;

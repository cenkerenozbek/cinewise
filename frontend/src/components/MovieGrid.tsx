import { MovieCard } from './MovieCard';
import { WatchlistButton } from './WatchlistButton';
import type { MovieSummary } from '../lib/types';

interface MovieGridProps {
  movies: MovieSummary[];
  isLoading: boolean;
}

function SkeletonCard() {
  return (
    <div className="rounded-xl overflow-hidden animate-pulse" style={{ background: 'var(--cw-surface)' }}>
      <div className="aspect-[2/3]" style={{ background: 'var(--cw-surface-elevated)' }} />
      <div className="p-2.5 space-y-2">
        <div className="h-3 rounded w-3/4" style={{ background: 'var(--cw-surface-elevated)' }} />
        <div className="h-2 rounded w-1/2" style={{ background: 'var(--cw-surface-elevated)' }} />
      </div>
    </div>
  );
}

export function MovieGrid({ movies, isLoading }: MovieGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (movies.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-lg text-slate-400">No movies found</p>
        <p className="text-sm mt-1 text-slate-500">Try adjusting your search or filters</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {movies.map((movie) => (
        <MovieCard
            key={movie.tmdb_id}
            movie={movie}
            actionSlot={<WatchlistButton movieId={movie.tmdb_id} />}
          />
      ))}
    </div>
  );
}

export default MovieGrid;

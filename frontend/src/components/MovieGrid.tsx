import { MovieCard } from './MovieCard';
import type { MovieSummary } from '../lib/types';

interface MovieGridProps {
  movies: MovieSummary[];
  isLoading: boolean;
}

function SkeletonCard() {
  return (
    <div className="rounded-lg overflow-hidden bg-white shadow animate-pulse">
      <div className="aspect-[2/3] bg-gray-300" />
      <div className="p-2 space-y-2">
        <div className="h-3 bg-gray-300 rounded w-3/4" />
        <div className="h-2 bg-gray-200 rounded w-1/2" />
      </div>
    </div>
  );
}

export function MovieGrid({ movies, isLoading }: MovieGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (movies.length === 0) {
    return (
      <div className="text-center py-20 text-gray-500">
        <p className="text-lg">No movies found</p>
        <p className="text-sm mt-1">Try adjusting your search or filters</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {movies.map((movie) => (
        <MovieCard key={movie.tmdb_id} movie={movie} />
      ))}
    </div>
  );
}

export default MovieGrid;

import { Link } from 'react-router-dom';
import { useWatchlist, useToggleWatchlist } from '../hooks/useWatchlist';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w300';

function WatchlistCard({ item }: { item: { movie_id: number; title: string; poster_path: string | null; year: number | null; rating: number | null; genres: string[] } }) {
  const { removeMutation } = useToggleWatchlist(item.movie_id);
  return (
    <div className="rounded-xl overflow-hidden group" style={{ background: 'var(--cw-surface)' }}>
      <Link to={`/movie/${item.movie_id}`}>
        <div className="relative aspect-[2/3]" style={{ background: 'var(--cw-surface-elevated)' }}>
          {item.poster_path && (
            <img src={`${TMDB_POSTER_BASE}${item.poster_path}`} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
          )}
          {item.rating != null && (
            <div className="absolute top-2 right-2 bg-amber-400 text-amber-900 text-xs font-bold px-2 py-0.5 rounded-full">
              ★ {item.rating.toFixed(1)}
            </div>
          )}
        </div>
      </Link>
      <div className="p-2.5">
        <p className="text-sm font-semibold text-slate-100 truncate">{item.title}</p>
        <div className="flex items-center justify-between mt-1">
          {item.year && <p className="text-xs text-slate-400">{item.year}</p>}
          <button
            type="button"
            onClick={() => removeMutation.mutate()}
            disabled={removeMutation.isPending}
            className="text-xs text-slate-500 hover:text-red-400 transition-colors"
            title="Remove from watchlist"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}

export function WatchlistPage() {
  const { data, isLoading } = useWatchlist();
  const items = data?.items ?? [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-100 mb-6">My Watchlist</h1>

      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-xl animate-pulse" style={{ background: 'var(--cw-surface)' }}>
              <div className="aspect-[2/3]" style={{ background: 'var(--cw-surface-elevated)' }} />
            </div>
          ))}
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="text-center py-20">
          <p className="text-slate-400 text-lg">Your watchlist is empty.</p>
          <p className="text-slate-500 text-sm mt-2">Browse movies and click the bookmark icon to save them.</p>
          <Link
            to="/"
            className="mt-4 inline-flex items-center px-4 py-2 rounded-xl font-bold text-white transition-opacity hover:opacity-90"
            style={{ background: 'var(--cw-accent)' }}
          >
            Browse Movies
          </Link>
        </div>
      )}

      {!isLoading && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {items.map((item) => (
            <WatchlistCard key={item.movie_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default WatchlistPage;

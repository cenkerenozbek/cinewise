import { useAuth } from '../hooks/useAuth';
import { useWatchlist, useToggleWatchlist } from '../hooks/useWatchlist';

interface WatchlistButtonProps {
  movieId: number;
  size?: 'sm' | 'md';
  className?: string;
}

export function WatchlistButton({ movieId, size = 'sm', className = '' }: WatchlistButtonProps) {
  const { isAuthenticated } = useAuth();
  const { data: watchlistData } = useWatchlist();
  const { addMutation, removeMutation } = useToggleWatchlist(movieId);

  if (!isAuthenticated) return null;

  const isInWatchlist = watchlistData?.items.some((i) => i.movie_id === movieId) ?? false;
  const isPending = addMutation.isPending || removeMutation.isPending;

  function handleToggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (isInWatchlist) {
      removeMutation.mutate();
    } else {
      addMutation.mutate();
    }
  }

  const dim = size === 'md' ? 'w-10 h-10' : 'w-8 h-8';
  const iconDim = size === 'md' ? 'h-5 w-5' : 'h-4 w-4';

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={isPending}
      className={`${dim} rounded-full flex items-center justify-center transition-all disabled:opacity-50 ${
        isInWatchlist
          ? 'text-white shadow-lg'
          : 'bg-black/60 text-white/80 hover:text-white hover:bg-black/80'
      } ${className}`}
      style={isInWatchlist ? { background: 'var(--cw-accent)' } : undefined}
      title={isInWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
    >
      {isInWatchlist ? (
        <svg xmlns="http://www.w3.org/2000/svg" className={iconDim} viewBox="0 0 24 24" fill="currentColor">
          <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" className={iconDim} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
      )}
    </button>
  );
}

export default WatchlistButton;

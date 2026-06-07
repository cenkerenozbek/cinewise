import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useHistoryList } from '../hooks/useHistory';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w185';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'liked', label: 'Liked' },
  { key: 'disliked', label: 'Skipped' },
  { key: 'watched', label: 'Watched' },
] as const;

type FilterKey = typeof FILTERS[number]['key'];

function CompletionRing({ completion, size = 24 }: { completion: number; size?: number }) {
  const r = size / 2 - 3;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - completion);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2.5" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="#f59e0b"
        strokeWidth="2.5"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x={size / 2} y={size / 2 + 0.5} textAnchor="middle" dominantBaseline="middle" fontSize="6" fill="#f59e0b" fontWeight="700">
        {Math.round(completion * 100)}%
      </text>
    </svg>
  );
}

export function HistoryPage() {
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all');
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data, isLoading } = useHistoryList(page, activeFilter);

  const deleteMutation = useMutation({
    mutationFn: async (movieId: number) => {
      await api.delete(`/feedback/${movieId}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['history'] });
    },
  });

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Watch History</h1>
        <Link to="/profile" className="text-sm font-medium hover:underline" style={{ color: 'var(--cw-accent)' }}>
          Profile
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => { setActiveFilter(f.key); setPage(1); }}
            className="px-4 py-1.5 rounded-full text-sm font-bold border transition-all"
            style={
              activeFilter === f.key
                ? { background: 'var(--cw-accent)', borderColor: 'var(--cw-accent)', color: '#fff' }
                : { background: 'transparent', borderColor: 'var(--cw-border)', color: '#94a3b8' }
            }
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-xl animate-pulse" style={{ background: 'var(--cw-surface)' }}>
              <div className="aspect-[2/3]" style={{ background: 'var(--cw-surface-elevated)' }} />
              <div className="p-2 space-y-1">
                <div className="h-3 rounded w-3/4" style={{ background: 'var(--cw-surface-elevated)' }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && data?.items.length === 0 && (
        <div className="text-center py-20">
          <p className="text-slate-400">No history yet.</p>
          <Link to="/" className="mt-3 inline-block text-sm font-medium hover:underline" style={{ color: 'var(--cw-accent)' }}>
            Browse Movies
          </Link>
        </div>
      )}

      {!isLoading && data && data.items.length > 0 && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {data.items.map((item) => (
              <div key={item.movie_id} className="relative group rounded-xl overflow-hidden" style={{ background: 'var(--cw-surface)' }}>
                <Link to={`/movie/${item.movie_id}`}>
                  <div className="relative aspect-[2/3]" style={{ background: 'var(--cw-surface-elevated)' }}>
                    {item.poster_path && (
                      <img src={`${TMDB_POSTER_BASE}${item.poster_path}`} alt={item.title} className="w-full h-full object-cover" loading="lazy" />
                    )}
                    {/* Action overlay */}
                    <div className={`absolute inset-0 opacity-20 ${item.action === 'like' ? 'bg-green-500' : 'bg-red-500'}`} />
                    {/* Action badge */}
                    <div className={`absolute top-2 left-2 text-xs font-bold px-2 py-0.5 rounded-full ${
                      item.action === 'like'
                        ? 'bg-green-500/80 text-white'
                        : 'bg-red-500/80 text-white'
                    }`}>
                      {item.action === 'like' ? '👍' : '👎'}
                    </div>
                    {/* Completion ring */}
                    {item.watch_completion != null && (
                      <div className="absolute bottom-2 right-2">
                        <CompletionRing completion={item.watch_completion} size={30} />
                      </div>
                    )}
                  </div>
                </Link>
                <div className="p-2">
                  <p className="text-xs font-semibold text-slate-200 truncate">{item.title}</p>
                  {item.year && <p className="text-xs text-slate-500">{item.year}</p>}
                </div>
                {/* Remove button */}
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(item.movie_id)}
                  disabled={deleteMutation.isPending}
                  className="absolute top-2 right-2 w-6 h-6 rounded-full bg-black/60 text-white text-xs items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity flex"
                  title="Remove from history"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-4 py-2 text-sm font-medium border rounded-xl disabled:opacity-40 transition-colors"
                style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
              >
                Previous
              </button>
              <span className="text-sm text-slate-400">Page {page} of {data.total_pages}</span>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page >= data.total_pages}
                className="px-4 py-2 text-sm font-medium border rounded-xl disabled:opacity-40 transition-colors"
                style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default HistoryPage;

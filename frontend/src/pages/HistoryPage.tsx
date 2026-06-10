import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
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
  const [searchParams] = useSearchParams();
  const initialFilter = (searchParams.get('filter') as FilterKey | null) ?? 'all';
  const [activeFilter, setActiveFilter] = useState<FilterKey>(
    FILTERS.some(f => f.key === initialFilter) ? initialFilter : 'all'
  );
  const [page, setPage] = useState(1);

  useEffect(() => {
    const f = searchParams.get('filter') as FilterKey | null;
    if (f && FILTERS.some(fi => fi.key === f)) setActiveFilter(f);
  }, [searchParams]);
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
                    <div className={`absolute top-2 left-2 flex items-center justify-center w-6 h-6 rounded-full ${
                      item.action === 'like'
                        ? 'bg-green-500/80'
                        : 'bg-red-500/80'
                    }`}>
                      {item.action === 'like' ? (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                          <path d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                        </svg>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                          <path d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                        </svg>
                      )}
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

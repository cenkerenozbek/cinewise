import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export interface HistoryItem {
  movie_id: number;
  action: 'like' | 'dislike';
  watch_completion: number | null;
  updated_at: string;
  title: string;
  poster_path: string | null;
  genres: string[];
  year: number | null;
  rating: number | null;
}

export interface HistoryStats {
  total: number;
  liked: number;
  disliked: number;
  watched_count: number;
  avg_completion: number | null;
  genre_counts: Record<string, number>;
}

export function useHistoryStats() {
  return useQuery<HistoryStats>({
    queryKey: ['history', 'stats'],
    queryFn: async () => {
      const res = await api.get('/history/stats');
      return res.data;
    },
    staleTime: 30_000,
    retry: false,
  });
}

export function useHistoryList(page = 1, filter = 'all') {
  return useQuery({
    queryKey: ['history', 'list', page, filter],
    queryFn: async () => {
      const res = await api.get('/history', { params: { page, filter } });
      return res.data as {
        items: HistoryItem[];
        total: number;
        page: number;
        page_size: number;
        total_pages: number;
      };
    },
    staleTime: 30_000,
    retry: false,
  });
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';

export interface WatchlistItem {
  movie_id: number;
  title: string;
  poster_path: string | null;
  genres: string[];
  year: number | null;
  rating: number | null;
}

export function useWatchlist() {
  return useQuery<{ items: WatchlistItem[] }>({
    queryKey: ['watchlist'],
    queryFn: async () => {
      const res = await api.get('/watchlist');
      return res.data;
    },
    staleTime: 30_000,
    retry: false,
  });
}

export function useToggleWatchlist(movieId: number) {
  const queryClient = useQueryClient();

  const addMutation = useMutation({
    mutationFn: async () => {
      await api.post('/watchlist', { movie_id: movieId });
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const removeMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/watchlist/${movieId}`);
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  return { addMutation, removeMutation };
}

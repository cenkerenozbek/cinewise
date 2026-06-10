import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { FeedbackAction } from '../lib/types';

export function useMovieFeedback(movieId: number, enabled = true) {
  return useQuery<{ action?: FeedbackAction; watch_completion?: number }>({
    queryKey: ['feedback', movieId],
    queryFn: async () => {
      const res = await api.get(`/feedback/${movieId}`);
      return res.data;
    },
    enabled: enabled && movieId > 0,
    staleTime: 1000 * 60 * 5,
  });
}

interface FeedbackPayload {
  movie_id: number;
  action: FeedbackAction;
  watch_completion?: number;
}

export function useFeedback() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, FeedbackPayload>({
    mutationFn: async (payload) => {
      await api.post('/feedback', payload);
    },
    onSuccess: () => {
      // Sadece history ve watchlist cache'ini güncelle;
      // recommendations kasıtlı olarak yenilenmez — kullanıcı sayfayı
      // yenileyene veya tercihleri değiştirene kadar liste değişmemeli.
      void queryClient.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

export function useDeleteFeedback() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: async (movieId) => {
      await api.delete(`/feedback/${movieId}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

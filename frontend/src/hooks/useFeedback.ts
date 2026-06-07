import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { FeedbackAction } from '../lib/types';

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

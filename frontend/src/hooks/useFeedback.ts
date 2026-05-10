import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { FeedbackAction } from '../lib/types';

interface FeedbackPayload {
  movie_id: number;
  action: FeedbackAction;
}

export function useFeedback() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, FeedbackPayload>({
    mutationFn: async (payload) => {
      await api.post('/feedback', payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

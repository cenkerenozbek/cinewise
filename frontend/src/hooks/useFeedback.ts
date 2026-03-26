import { useMutation } from '@tanstack/react-query';
import api from '../lib/api';
import type { FeedbackAction } from '../lib/types';

interface FeedbackPayload {
  movie_id: number;
  action: FeedbackAction;
}

export function useFeedback() {
  return useMutation<void, Error, FeedbackPayload>({
    mutationFn: async (payload) => {
      await api.post('/feedback', payload);
    },
  });
}

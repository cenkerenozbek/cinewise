import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { RecommendationResponse, UserPreferences } from '../lib/types';

export function useRecommendations(
  genres: string[],
  mood: string | null,
  authCacheKey = 'anonymous',
) {
  const queryClient = useQueryClient();

  return useQuery<RecommendationResponse>({
    queryKey: ['recommendations', genres, mood, authCacheKey],
    queryFn: async () => {
      const { data } = await api.post<RecommendationResponse>('/recommendations', {
        genres,
        mood,
      });
      if (authCacheKey !== 'anonymous') {
        void queryClient.invalidateQueries({ queryKey: ['userPreferences', authCacheKey] });
      }
      return data;
    },
    enabled: genres.length > 0,
  });
}

export function useUserPreferences(enabled = true, authCacheKey = 'anonymous') {
  return useQuery<UserPreferences>({
    queryKey: ['userPreferences', authCacheKey],
    queryFn: async () => {
      const { data } = await api.get<UserPreferences>('/recommendations/preferences');
      return data;
    },
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useSaveUserPreferences(authCacheKey = 'anonymous') {
  const queryClient = useQueryClient();

  return useMutation<UserPreferences, Error, UserPreferences>({
    mutationFn: async (preferences) => {
      const { data } = await api.post<UserPreferences>(
        '/recommendations/preferences',
        preferences,
      );
      return data;
    },
    onSuccess: (preferences) => {
      queryClient.setQueryData(['userPreferences', authCacheKey], preferences);
      void queryClient.invalidateQueries({ queryKey: ['userPreferences', authCacheKey] });
    },
  });
}

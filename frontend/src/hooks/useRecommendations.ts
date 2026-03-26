import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { RecommendationResponse, UserPreferences } from '../lib/types';

export function useRecommendations(genres: string[], mood: string | null) {
  return useQuery<RecommendationResponse>({
    queryKey: ['recommendations', genres, mood],
    queryFn: async () => {
      const { data } = await api.post<RecommendationResponse>('/recommendations', {
        genres,
        mood,
      });
      return data;
    },
    enabled: genres.length > 0,
  });
}

export function useUserPreferences() {
  return useQuery<UserPreferences>({
    queryKey: ['userPreferences'],
    queryFn: async () => {
      const { data } = await api.get<UserPreferences>('/recommendations/preferences');
      return data;
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

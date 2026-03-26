import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { MetricsData } from '../lib/types';

export function useMetrics() {
  return useQuery<MetricsData | null>({
    queryKey: ['metrics'],
    queryFn: async () => {
      try {
        const { data } = await api.get<MetricsData>('/metrics');
        return data;
      } catch (err: any) {
        if (err?.response?.status === 404) return null;
        throw err;
      }
    },
    staleTime: 60 * 60 * 1000, // 1 hour -- metrics don't change during a session
    retry: false,
  });
}

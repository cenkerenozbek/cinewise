import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';

interface UserProfile {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
}

export function useProfile() {
  return useQuery<UserProfile>({
    queryKey: ['profile'],
    queryFn: async () => {
      const { data } = await api.get<UserProfile>('/auth/profile');
      return data;
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (fields: { first_name?: string; last_name?: string }) => {
      const { data } = await api.patch<UserProfile>('/auth/profile', fields);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}

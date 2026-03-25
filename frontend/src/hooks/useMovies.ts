import { useQuery } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import api from '../lib/api';
import type { MovieListResponse, MovieDetail } from '../lib/types';

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function useMovieSearch(query: string, genre: string, year: string, page: number = 1) {
  const debouncedQuery = useDebouncedValue(query, 300);
  return useQuery<MovieListResponse>({
    queryKey: ['movies', 'search', debouncedQuery, genre, year, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (debouncedQuery) params.set('q', debouncedQuery);
      if (genre) params.set('genre', genre);
      if (year) params.set('year', year);
      params.set('page', String(page));
      params.set('page_size', '20');
      const { data } = await api.get<MovieListResponse>(`/movies?${params}`);
      return data;
    },
  });
}

export function useMovieDetail(tmdbId: number) {
  return useQuery<MovieDetail>({
    queryKey: ['movie', tmdbId],
    queryFn: async () => {
      const { data } = await api.get<MovieDetail>(`/movies/${tmdbId}`);
      return data;
    },
    enabled: !!tmdbId,
  });
}

export function useGenres() {
  return useQuery<string[]>({
    queryKey: ['genres'],
    queryFn: async () => {
      const { data } = await api.get<{ genres: string[] }>('/movies/genres');
      return data.genres;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

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

export function useMovieTrailer(tmdbId: number) {
  return useQuery<{ youtube_key: string | null }>({
    queryKey: ['movie-trailer', tmdbId],
    queryFn: async () => {
      const { data } = await api.get<{ youtube_key: string | null }>(`/movies/${tmdbId}/trailer`);
      return data;
    },
    enabled: !!tmdbId,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

export function usePopularMovies(count: number) {
  return useQuery<MovieListResponse>({
    queryKey: ['movies', 'popular', count],
    queryFn: async () => {
      const { data } = await api.get<MovieListResponse>(
        `/movies?sort_by=votes&min_votes=50000&min_rating=7.0&page_size=${count}`
      );
      return data;
    },
    staleTime: 10 * 60 * 1000,
  });
}

export function useForYouMovies(primaryGenre: string, pageSize: number) {
  return useQuery<MovieListResponse>({
    queryKey: ['for-you-movies', primaryGenre, pageSize],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (primaryGenre) params.set('genre', primaryGenre);
      params.set('page_size', String(pageSize));
      const { data } = await api.get<MovieListResponse>(`/movies?${params}`);
      return data;
    },
    enabled: !!primaryGenre && pageSize > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSimilarMovies(tmdbId: number, genres: string[]) {
  const primaryGenre = genres[0] ?? '';
  return useQuery<MovieListResponse>({
    queryKey: ['similar-movies', tmdbId, primaryGenre],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (primaryGenre) params.set('genre', primaryGenre);
      params.set('page_size', '13');
      const { data } = await api.get<MovieListResponse>(`/movies?${params}`);
      return data;
    },
    enabled: !!tmdbId && genres.length > 0,
    staleTime: 10 * 60 * 1000,
  });
}

export function useBrowseAll(pageSize: number) {
  return useQuery<MovieListResponse>({
    queryKey: ['movies', 'browse', pageSize],
    queryFn: async () => {
      const { data } = await api.get<MovieListResponse>(`/movies?page_size=${pageSize}`);
      return data;
    },
    staleTime: 5 * 60 * 1000,
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

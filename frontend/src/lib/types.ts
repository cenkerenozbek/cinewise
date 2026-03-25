export interface MovieSummary {
  tmdb_id: number;
  title: string;
  title_tr: string | null;
  year: number | null;
  genres: string[];
  poster_path: string | null;
  rating: number | null;
}

export interface MovieDetail extends MovieSummary {
  overview: string | null;
  vote_count: number | null;
  popularity: number | null;
  director: string | null;
  cast: string[];
}

export interface MovieListResponse {
  movies: MovieSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: string;
  email: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

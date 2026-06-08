import { createContext, useContext, useEffect, useState } from 'react';

interface MoodTheme {
  bg: string;
  surface: string;
  surfaceElevated: string;
  accent: string;
  accentHover: string;
  border: string;
}

const MOOD_THEMES_DARK: Record<string, MoodTheme> = {
  default:       { bg: '#0f0f14', surface: '#1a1a24', surfaceElevated: '#22222f', accent: '#6366f1', accentHover: '#818cf8', border: 'rgba(255,255,255,0.08)' },
  Happy:         { bg: '#1a1008', surface: '#22180a', surfaceElevated: '#2e2010', accent: '#f59e0b', accentHover: '#fbbf24', border: 'rgba(255,255,255,0.08)' },
  Tense:         { bg: '#071a14', surface: '#0a2218', surfaceElevated: '#0e2e22', accent: '#2dd4bf', accentHover: '#5eead4', border: 'rgba(255,255,255,0.08)' },
  Relaxing:      { bg: '#0e1220', surface: '#161b2e', surfaceElevated: '#1e2440', accent: '#b8a4ed', accentHover: '#c4b5f4', border: 'rgba(255,255,255,0.08)' },
  'Mind-bending':{ bg: '#120a1f', surface: '#1a1028', surfaceElevated: '#221434', accent: '#a855f7', accentHover: '#c084fc', border: 'rgba(255,255,255,0.08)' },
  Romantic:      { bg: '#1a0a10', surface: '#220e14', surfaceElevated: '#2e1220', accent: '#fb7185', accentHover: '#fda4af', border: 'rgba(255,255,255,0.08)' },
};

const MOOD_THEMES_LIGHT: Record<string, MoodTheme> = {
  default:       { bg: '#ffffff', surface: '#f9fafb', surfaceElevated: '#f3f4f6', accent: '#be123c', accentHover: '#9f1239', border: 'rgba(0,0,0,0.1)' },
  Happy:         { bg: '#fffbeb', surface: '#ffffff', surfaceElevated: '#fef9c3', accent: '#d97706', accentHover: '#b45309', border: 'rgba(0,0,0,0.08)' },
  Tense:         { bg: '#f0fdfa', surface: '#ffffff', surfaceElevated: '#ccfbf1', accent: '#0d9488', accentHover: '#0f766e', border: 'rgba(0,0,0,0.08)' },
  Relaxing:      { bg: '#f5f3ff', surface: '#ffffff', surfaceElevated: '#ede9fe', accent: '#7c3aed', accentHover: '#6d28d9', border: 'rgba(0,0,0,0.08)' },
  'Mind-bending':{ bg: '#faf5ff', surface: '#ffffff', surfaceElevated: '#f3e8ff', accent: '#9333ea', accentHover: '#7e22ce', border: 'rgba(0,0,0,0.08)' },
  Romantic:      { bg: '#fff1f2', surface: '#ffffff', surfaceElevated: '#ffe4e6', accent: '#e11d48', accentHover: '#be123c', border: 'rgba(0,0,0,0.08)' },
};

interface MoodThemeContextValue {
  activeMood: string | null;
  setActiveMood: (mood: string | null) => void;
  currentTheme: MoodTheme;
  isDark: boolean;
  toggleTheme: () => void;
}

const MoodThemeContext = createContext<MoodThemeContextValue>({
  activeMood: null,
  setActiveMood: () => {},
  currentTheme: MOOD_THEMES_DARK.default,
  isDark: true,
  toggleTheme: () => {},
});

export function MoodThemeProvider({ children }: { children: React.ReactNode }) {
  const [activeMood, setActiveMood] = useState<string | null>(null);
  const [isDark, setIsDark] = useState<boolean>(() => {
    try {
      return localStorage.getItem('cw-theme') === 'dark';
    } catch {
      return false;
    }
  });

  const themes = isDark ? MOOD_THEMES_DARK : MOOD_THEMES_LIGHT;
  const currentTheme = themes[activeMood ?? 'default'] ?? themes.default;

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', isDark ? 'dark' : 'light');
    root.style.setProperty('--cw-bg', currentTheme.bg);
    root.style.setProperty('--cw-surface', currentTheme.surface);
    root.style.setProperty('--cw-surface-elevated', currentTheme.surfaceElevated);
    root.style.setProperty('--cw-accent', currentTheme.accent);
    root.style.setProperty('--cw-accent-hover', currentTheme.accentHover);
    root.style.setProperty('--cw-border', currentTheme.border);
    root.style.background = currentTheme.bg;
  }, [currentTheme, isDark]);

  function toggleTheme() {
    setIsDark((prev) => {
      const next = !prev;
      try { localStorage.setItem('cw-theme', next ? 'dark' : 'light'); } catch {}
      return next;
    });
  }

  return (
    <MoodThemeContext.Provider value={{ activeMood, setActiveMood, currentTheme, isDark, toggleTheme }}>
      {children}
    </MoodThemeContext.Provider>
  );
}

export function useMoodTheme() {
  return useContext(MoodThemeContext);
}

export { MOOD_THEMES_DARK as MOOD_THEMES };

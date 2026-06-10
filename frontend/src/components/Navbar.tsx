import { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthContext } from '../features/auth/auth-context';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import { useProfile } from '../hooks/useProfile';
import { useUserPreferences, useSaveUserPreferences } from '../hooks/useRecommendations';
import { AVATARS } from '../lib/avatars';

const MOOD_OPTIONS = [
  { key: 'Happy',        icon: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z', color: '#f59e0b' },
  { key: 'Tense',        icon: 'M13 10V3L4 14h7v7l9-11h-7z',                                                                                                                         color: '#2dd4bf' },
  { key: 'Relaxing',     icon: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z',                                                               color: '#b8a4ed' },
  { key: 'Mind-bending', icon: 'M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z', color: '#a855f7' },
  { key: 'Romantic',     icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',                       color: '#fb7185' },
];

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthContext();
  const { isDark, toggleTheme, activeMood, setActiveMood } = useMoodTheme();
  const { data: profile } = useProfile({ enabled: isAuthenticated });
  const { data: savedPrefs } = useUserPreferences(isAuthenticated, user?.id ?? 'anonymous');
  const saveMutation = useSaveUserPreferences(user?.id ?? 'anonymous');
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchQuery = searchParams.get('q') ?? '';
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [moodOpen, setMoodOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const moodRef = useRef<HTMLDivElement>(null);
  const searchOriginRef = useRef<string | null>(null);

  const isHomePage = location.pathname === '/';

  // Close dropdowns on outside click
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
      if (moodRef.current && !moodRef.current.contains(e.target as Node)) {
        setMoodOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  // Reset origin ref when user navigates away from home via other means
  useEffect(() => {
    if (location.pathname !== '/') {
      searchOriginRef.current = null;
    }
  }, [location.pathname]);

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    if (location.pathname !== '/') {
      searchOriginRef.current = location.pathname;
      navigate(`/?q=${encodeURIComponent(value)}`);
    } else if (!value && searchOriginRef.current) {
      const origin = searchOriginRef.current;
      searchOriginRef.current = null;
      navigate(origin);
    } else {
      setSearchParams(value ? { q: value } : {}, { replace: true });
    }
  }

  function handleClearSearch() {
    if (searchOriginRef.current) {
      const origin = searchOriginRef.current;
      searchOriginRef.current = null;
      navigate(origin);
    } else {
      setSearchParams({}, { replace: true });
    }
  }

  function handleMoodSelect(key: string | null) {
    const next = key === activeMood ? null : key;
    setActiveMood(next);
    setMoodOpen(false);
    if (isAuthenticated) {
      saveMutation.mutate({ genres: savedPrefs?.genres ?? [], mood: next ?? undefined });
    }
  }

  function handleLogout() {
    logout();
    setDropdownOpen(false);
    navigate('/');
  }

  const navBg = isHomePage
    ? 'bg-transparent'
    : isDark
      ? 'bg-gray-950/95 backdrop-blur-md border-b border-white/5'
      : 'bg-white shadow-sm border-b border-gray-100';

  const textColor = isHomePage || isDark ? '#ffffff' : '#111827';
  const mutedColor = isHomePage || isDark ? 'rgba(255,255,255,0.7)' : '#6b7280';
  const searchBg = isHomePage ? 'rgba(0,0,0,0.35)' : isDark ? 'var(--cw-surface)' : '#f3f4f6';
  const searchBorder = isHomePage ? 'rgba(255,255,255,0.2)' : isDark ? 'var(--cw-border)' : '#d1d5db';

  const displayName = [profile?.first_name, profile?.last_name].filter(Boolean).join(' ') || null;
  const initial = displayName?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? '?';
  const avatarFile = AVATARS.find(a => a.id === profile?.avatar_id)?.file ?? null;

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 px-6 py-0 flex items-center gap-4 h-[64px] transition-all duration-300 ${navBg}`}>
      {/* Logo */}
      <Link to="/" className="shrink-0 hover:opacity-80 transition-opacity">
        {isDark ? (
          <img src="/cinewise-logo-dark.webp" alt="Cinewise" className="h-[42px] w-auto object-contain" />
        ) : (
          <picture>
            <source srcSet="/cinewise-logo.webp" type="image/webp" />
            <img src="/cinewise-logo.png" alt="Cinewise" className="h-[42px] w-auto object-contain" />
          </picture>
        )}
      </Link>

      {/* Search */}
      <div className="relative flex-1 max-w-lg mx-auto">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: mutedColor }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 105 11a6 6 0 0012 0z" />
          </svg>
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={handleSearchChange}
          placeholder="Search by title, actor or director…"
          className={`w-full pl-9 pr-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--cw-accent)] transition-all ${isHomePage ? 'placeholder-white/50' : isDark ? 'placeholder-slate-500' : 'placeholder-gray-400'}`}
          style={{ background: searchBg, border: `1.5px solid ${searchBorder}`, color: textColor }}
        />
        {searchQuery && (
          <button
            type="button"
            onClick={handleClearSearch}
            className="absolute inset-y-0 right-2 flex items-center px-1"
            style={{ color: mutedColor }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Mood picker */}
        <div className="relative" ref={moodRef}>
          <button
            type="button"
            onClick={() => setMoodOpen((v) => !v)}
            className="flex items-center gap-2 rounded-full pl-2.5 pr-2 py-1 transition-all hover:opacity-90"
            style={{
              background: activeMood ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)',
              backdropFilter: 'blur(8px)',
              border: `1px solid ${activeMood ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.1)'}`,
            }}
          >
            {activeMood ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                style={{ color: MOOD_OPTIONS.find(m => m.key === activeMood)?.color }}>
                <path d={MOOD_OPTIONS.find(m => m.key === activeMood)?.icon} />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                style={{ color: mutedColor }}>
                <path d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            <span className="text-xs font-medium" style={{ color: activeMood ? textColor : mutedColor }}>
              {activeMood ?? 'Mood'}
            </span>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 transition-transform duration-200 shrink-0" style={{ color: mutedColor, transform: moodOpen ? 'rotate(180deg)' : 'rotate(0deg)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {moodOpen && (
            <div
              className="absolute right-0 top-[calc(100%+8px)] w-44 rounded-xl overflow-hidden shadow-xl z-50"
              style={{
                background: isDark ? '#1e2130' : '#ffffff',
                border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#e5e7eb'}`,
              }}
            >
              <div className="px-3 py-2 border-b text-xs font-semibold" style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : '#f3f4f6', color: isDark ? '#94a3b8' : '#6b7280' }}>
                Mood
              </div>
              {MOOD_OPTIONS.map(({ key, icon, color }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleMoodSelect(key)}
                  className="flex items-center gap-2.5 w-full px-3 py-2 text-sm transition-colors hover:opacity-80"
                  style={{
                    color: isDark ? '#e2e8f0' : '#111827',
                    background: activeMood === key ? (isDark ? 'rgba(255,255,255,0.06)' : '#f3f4f6') : 'transparent',
                    fontWeight: activeMood === key ? 600 : 400,
                  }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ color }}>
                    <path d={icon} />
                  </svg>
                  {key}
                </button>
              ))}
              {activeMood && (
                <div className="border-t" style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : '#f3f4f6' }}>
                  <button
                    type="button"
                    onClick={() => handleMoodSelect(null)}
                    className="flex items-center gap-2.5 w-full px-3 py-2 text-sm hover:opacity-80 transition-colors"
                    style={{ color: isDark ? '#94a3b8' : '#6b7280' }}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Clear mood
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {isAuthenticated && user ? (
          <>
            {/* Profile dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen((v) => !v)}
                className="flex items-center gap-2 rounded-full pl-1 pr-3 py-1 transition-all hover:opacity-90"
                style={{
                  background: isHomePage || isDark ? 'rgba(255,255,255,0.12)' : 'var(--cw-surface-elevated)',
                  backdropFilter: 'blur(8px)',
                  border: `1px solid ${isHomePage || isDark ? 'rgba(255,255,255,0.2)' : 'var(--cw-border)'}`,
                }}
              >
                {/* Avatar */}
                {avatarFile ? (
                  <img
                    src={avatarFile}
                    alt="avatar"
                    className="w-7 h-7 rounded-full object-cover flex-shrink-0"
                  />
                ) : (
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                    style={{ background: 'var(--cw-accent)' }}
                  >
                    {initial}
                  </div>
                )}
                <span className="text-sm font-medium max-w-[160px] truncate" style={{ color: textColor }}>
                  {displayName ?? user.email.split('@')[0]}
                </span>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 transition-transform duration-200" style={{ color: mutedColor, transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Dropdown */}
              {dropdownOpen && (
                <div
                  className="absolute right-0 top-[calc(100%+8px)] w-48 rounded-xl overflow-hidden shadow-xl z-50"
                  style={{
                    background: isDark ? '#1e2130' : '#ffffff',
                    border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#e5e7eb'}`,
                  }}
                >
                  {/* User info */}
                  <div className="px-4 py-3 border-b" style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : '#f3f4f6' }}>
                    <p className="text-xs font-medium truncate" style={{ color: isDark ? '#94a3b8' : '#6b7280' }}>
                      {user.email}
                    </p>
                  </div>

                  {/* Menu items */}
                  {[
                    { to: '/recommendations', label: 'For You', icon: 'M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z' },
                    { to: '/profile', label: 'Profile', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
                    { to: '/watchlist', label: 'Watchlist', icon: 'M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z' },
                    { to: '/history', label: 'Watch History', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
                  ].map(({ to, label, icon }) => (
                    <Link
                      key={to}
                      to={to}
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors hover:opacity-80"
                      style={{ color: isDark ? '#e2e8f0' : '#111827' }}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                        <path d={icon} />
                      </svg>
                      {label}
                    </Link>
                  ))}

                  <div className="border-t" style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : '#f3f4f6' }}>
                    {/* Theme toggle row */}
                    <button
                      type="button"
                      onClick={toggleTheme}
                      className="flex items-center justify-between w-full px-4 py-2.5 text-sm transition-colors hover:opacity-80"
                      style={{ color: isDark ? '#e2e8f0' : '#111827' }}
                    >
                      <div className="flex items-center gap-3">
                        {isDark ? (
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0 text-amber-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ color: '#6b7280' }}>
                            <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                          </svg>
                        )}
                        Dark mode
                      </div>
                      {/* Pill toggle */}
                      <div
                        className="w-8 h-4 rounded-full relative transition-colors duration-200 flex-shrink-0"
                        style={{ background: isDark ? 'var(--cw-accent)' : '#d1d5db' }}
                      >
                        <div
                          className="absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform duration-200"
                          style={{ transform: isDark ? 'translateX(18px)' : 'translateX(2px)' }}
                        />
                      </div>
                    </button>
                  </div>

                  <div className="border-t" style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : '#f3f4f6' }}>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex items-center gap-3 w-full px-4 py-2.5 text-sm transition-colors hover:opacity-80"
                      style={{ color: '#f87171' }}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: textColor }}>
              Sign in
            </Link>
            <Link
              to="/register"
              className="px-4 py-2 text-sm font-medium rounded-lg text-white transition-opacity hover:opacity-90"
              style={{ background: 'var(--cw-accent)' }}
            >
              Register
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navbar;

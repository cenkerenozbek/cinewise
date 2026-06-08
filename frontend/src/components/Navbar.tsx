import { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthContext } from '../features/auth/auth-context';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import { useProfile } from '../hooks/useProfile';

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthContext();
  const { isDark, toggleTheme } = useMoodTheme();
  const { data: profile } = useProfile();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchQuery = searchParams.get('q') ?? '';
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isHomePage = location.pathname === '/';

  // Close dropdown on outside click
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    if (location.pathname !== '/') {
      navigate(`/?q=${encodeURIComponent(value)}`);
    } else {
      setSearchParams(value ? { q: value } : {}, { replace: true });
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

  const logoColor = isHomePage || isDark ? '#ffffff' : '#111827';
  const textColor = isHomePage || isDark ? '#ffffff' : '#111827';
  const mutedColor = isHomePage || isDark ? 'rgba(255,255,255,0.7)' : '#6b7280';
  const searchBg = isHomePage ? 'rgba(0,0,0,0.35)' : isDark ? 'var(--cw-surface)' : '#f3f4f6';
  const searchBorder = isHomePage ? 'rgba(255,255,255,0.2)' : isDark ? 'var(--cw-border)' : '#d1d5db';

  const displayName = [profile?.first_name, profile?.last_name].filter(Boolean).join(' ') || null;
  const initial = displayName?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? '?';

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 px-6 py-0 flex items-center gap-4 h-[64px] transition-all duration-300 ${navBg}`}>
      {/* Logo */}
      <Link to="/" className="flex items-center gap-3 shrink-0 hover:opacity-80 transition-opacity">
        <div className="w-[42px] h-[42px] rounded-lg flex items-center justify-center" style={{ background: 'var(--cw-accent)' }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
          </svg>
        </div>
        <span className="text-xl font-bold tracking-wide" style={{ color: logoColor }}>
          Cinewise
        </span>
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
          placeholder="What do you want to watch?"
          className={`w-full pl-9 pr-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--cw-accent)] transition-all ${isHomePage ? 'placeholder-white/50' : isDark ? 'placeholder-slate-500' : 'placeholder-gray-400'}`}
          style={{ background: searchBg, border: `1.5px solid ${searchBorder}`, color: textColor }}
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchParams({}, { replace: true })}
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
        {/* Theme toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:opacity-80"
        >
          {isDark ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-amber-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ color: mutedColor }}>
              <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>

        {isAuthenticated && user ? (
          <>
            {/* Profile dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen((v) => !v)}
                className="flex items-center gap-2 rounded-full pl-1 pr-3 py-1 transition-all hover:opacity-90"
                style={{
                  background: isHomePage || isDark ? 'rgba(255,255,255,0.1)' : 'var(--cw-surface-elevated)',
                  border: `1px solid ${isHomePage || isDark ? 'rgba(255,255,255,0.15)' : 'var(--cw-border)'}`,
                }}
              >
                {/* Avatar */}
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                  style={{ background: 'var(--cw-accent)' }}
                >
                  {initial}
                </div>
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

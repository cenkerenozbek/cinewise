import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthContext } from '../features/auth/auth-context';
import { useMoodTheme } from '../features/mood/MoodThemeContext';

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthContext();
  const { isDark, toggleTheme } = useMoodTheme();
  const location = useLocation();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/');
  }

  const navLink = (to: string, label: string) => (
    <Link
      to={to}
      className={`text-sm transition-colors ${
        location.pathname === to
          ? 'text-[var(--cw-accent)] border-b-2 border-[var(--cw-accent)] pb-0.5'
          : 'text-slate-300 hover:text-[var(--cw-accent)]'
      }`}
    >
      {label}
    </Link>
  );

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-950/90 backdrop-blur-md border-b border-white/5 text-white px-6 py-3 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2 text-xl font-bold tracking-wide hover:text-[var(--cw-accent)] transition-colors">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--cw-accent)]">
          <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
          <line x1="7" y1="2" x2="7" y2="22"/>
          <line x1="17" y1="2" x2="17" y2="22"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <line x1="2" y1="7" x2="7" y2="7"/>
          <line x1="2" y1="17" x2="7" y2="17"/>
          <line x1="17" y1="17" x2="22" y2="17"/>
          <line x1="17" y1="7" x2="22" y2="7"/>
        </svg>
        Cinewise
      </Link>
      <div className="flex items-center gap-5">
          {/* Dark / Light toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="w-9 h-9 rounded-full flex items-center justify-center transition-all hover:scale-110"
            style={{ background: 'var(--cw-surface-elevated)', border: '1px solid var(--cw-border)' }}
          >
            {isDark ? (
              /* Sun icon */
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4.5 w-4.5 text-amber-300" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.166 17.834a.75.75 0 00-1.06 1.06l1.59 1.591a.75.75 0 001.061-1.06l-1.59-1.591zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.166 6.166a.75.75 0 001.06 1.06l1.591-1.59a.75.75 0 10-1.061-1.061l-1.59 1.59z" />
              </svg>
            ) : (
              /* Moon icon */
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4.5 w-4.5 text-slate-600" viewBox="0 0 24 24" fill="currentColor">
                <path fillRule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clipRule="evenodd" />
              </svg>
            )}
          </button>
        {isAuthenticated && user ? (
          <>
            {navLink('/recommendations', 'For You')}
            {navLink('/profile', 'Profile')}
            {navLink('/history', 'History')}
            {navLink('/watchlist', 'Watchlist')}
            <span className="text-sm text-slate-400 hidden sm:block">{user.email}</span>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 text-sm bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link
              to="/login"
              className="px-3 py-1.5 text-sm text-slate-300 hover:text-[var(--cw-accent)] transition-colors"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="px-3 py-1.5 text-sm bg-[var(--cw-accent)] hover:opacity-90 rounded-lg transition-opacity font-medium"
            >
              Register
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}

export default Navbar;

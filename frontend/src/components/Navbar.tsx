import { Link } from 'react-router-dom';
import { useAuthContext } from '../features/auth/AuthContext';

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthContext();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-900 text-white px-6 py-3 flex items-center justify-between shadow-lg">
      <Link to="/" className="text-xl font-bold tracking-wide hover:text-blue-400 transition-colors">
        MovieMRS
      </Link>
      <div className="flex items-center gap-4">
        {isAuthenticated && user ? (
          <>
            <span className="text-sm text-gray-300 hidden sm:block">{user.email}</span>
            <button
              onClick={logout}
              className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link
              to="/login"
              className="px-3 py-1.5 text-sm hover:text-blue-400 transition-colors"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded transition-colors"
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

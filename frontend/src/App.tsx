import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './features/auth/AuthContext';
import { Navbar } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';

// Placeholder pages for routes not yet built (Task 2 will replace these)
function HomePagePlaceholder() {
  return <div className="pt-20 px-6 text-center text-gray-700">Movie grid loading...</div>;
}

function MovieDetailPagePlaceholder() {
  return <div className="pt-20 px-6 text-center text-gray-700">Movie detail loading...</div>;
}

function App() {
  return (
    <AuthProvider>
      <Navbar />
      <main className="pt-14">
        <Routes>
          <Route path="/" element={<HomePagePlaceholder />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/movie/:tmdbId" element={<MovieDetailPagePlaceholder />} />
        </Routes>
      </main>
    </AuthProvider>
  );
}

export default App;

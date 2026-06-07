import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthContext } from '../features/auth/auth-context';

export function RegisterPage() {
  const { register } = useAuthContext();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await register(email, password);
      navigate('/onboarding');
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setError('An account with this email already exists.');
      } else {
        setError('Registration failed. Please try again later.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div
        className="w-full max-w-md rounded-2xl border p-8 animate-fade-in-up"
        style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
      >
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-100">Join Cinewise</h1>
          <p className="text-sm text-slate-400 mt-1">Create your account and discover films you'll love</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2.5 rounded-xl border text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--cw-surface-elevated)', borderColor: 'var(--cw-border)' }}
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1.5">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 rounded-xl border text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--cw-surface-elevated)', borderColor: 'var(--cw-border)' }}
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1.5">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 rounded-xl border text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all"
              style={{ background: 'var(--cw-surface-elevated)', borderColor: 'var(--cw-border)' }}
              placeholder="Repeat your password"
            />
          </div>
          {error && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 font-bold rounded-xl disabled:opacity-50 transition-all text-white"
            style={{ background: 'var(--cw-accent)' }}
          >
            {submitting ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="font-medium" style={{ color: 'var(--cw-accent)' }}>
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;

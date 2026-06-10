import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useHistoryStats, useHistoryList } from '../hooks/useHistory';
import { TasteProfileChart } from '../components/TasteProfileChart';
import { useMoodTheme } from '../features/mood/MoodThemeContext';
import { useProfile, useUpdateProfile } from '../hooks/useProfile';
import { AVATARS } from '../lib/avatars';

const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w92';
const CF_THRESHOLD = 5;

export function ProfilePage() {
  const { user } = useAuth();
  const { activeMood, isDark } = useMoodTheme();
  const { data: stats, isLoading: statsLoading } = useHistoryStats();
  const { data: historyData } = useHistoryList(1, 'all');
  const { data: profile } = useProfile();
  const { mutate: updateProfile, isPending: isUpdating } = useUpdateProfile();

  const [editMode, setEditMode] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [editAvatar, setEditAvatar] = useState<string | null>(null);

  function openEdit() {
    setFirstName(profile?.first_name ?? '');
    setLastName(profile?.last_name ?? '');
    setEditAvatar(profile?.avatar_id ?? null);
    setEditMode(true);
  }

  function handleSave() {
    updateProfile(
      {
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        avatar_id: editAvatar ?? undefined,
      },
      { onSuccess: () => setEditMode(false) },
    );
  }

  const currentAvatarFile = AVATARS.find(a => a.id === profile?.avatar_id)?.file ?? null;

  const recentActivity = historyData?.items.slice(0, 5) ?? [];
  const displayName = [profile?.first_name, profile?.last_name].filter(Boolean).join(' ') || null;
  const initial = displayName?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? '?';
  const interactionCount = stats?.total ?? 0;
  const personalizationPct = Math.min(100, Math.round((interactionCount / CF_THRESHOLD) * 100));

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 animate-fade-in-up">
      {/* Header */}
      <div
        className="rounded-2xl border p-6 mb-6 flex items-center gap-4"
        style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
      >
        {currentAvatarFile ? (
          <img
            src={currentAvatarFile}
            alt="avatar"
            className="w-14 h-14 rounded-full object-cover flex-shrink-0"
            style={{ outline: '2px solid var(--cw-accent)', outlineOffset: '2px' }}
          />
        ) : (
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-black text-white flex-shrink-0"
            style={{ background: 'var(--cw-accent)' }}
          >
            {initial}
          </div>
        )}
        <div className="flex-1 min-w-0">
          {displayName && <p className="text-slate-100 font-bold truncate">{displayName}</p>}
          <p className="text-slate-400 text-sm truncate">{user?.email}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {activeMood && (
            <span
              className="px-3 py-1 rounded-full text-xs font-medium border"
              style={{ borderColor: 'var(--cw-accent)', color: 'var(--cw-accent)', background: 'var(--cw-accent)15' }}
            >
              {activeMood}
            </span>
          )}
          <button
            type="button"
            onClick={openEdit}
            className="px-3 py-1.5 text-xs font-medium rounded-lg border transition-all hover:opacity-80"
            style={{ borderColor: 'var(--cw-border)', color: 'var(--cw-accent)' }}
          >
            Edit Profile
          </button>
        </div>
      </div>

      {/* Edit profile form */}
      {editMode && (
        <div
          className="rounded-2xl border p-6 mb-6"
          style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
        >
          <h2 className="text-sm font-medium text-slate-300 mb-4">Edit Profile</h2>
          <div className="grid sm:grid-cols-2 gap-4 mb-5">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="First name"
                className="w-full px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--cw-accent)] text-slate-100"
                style={{ background: 'var(--cw-surface-elevated)', border: '1px solid var(--cw-border)' }}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Last name"
                className="w-full px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--cw-accent)] text-slate-100"
                style={{ background: 'var(--cw-surface-elevated)', border: '1px solid var(--cw-border)' }}
              />
            </div>
          </div>

          {/* Avatar picker */}
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Choose Avatar</label>
            <div className="grid grid-cols-6 gap-2">
              {AVATARS.map((avatar) => {
                const isSelected = editAvatar === avatar.id;
                return (
                  <button
                    key={avatar.id}
                    type="button"
                    title={avatar.name}
                    onClick={() => setEditAvatar(avatar.id)}
                    className="aspect-square rounded-lg overflow-hidden transition-all duration-150"
                    style={{
                      outline: isSelected ? '2px solid var(--cw-accent)' : '1px solid var(--cw-border)',
                      outlineOffset: isSelected ? '2px' : '0',
                      opacity: isSelected ? 1 : 0.6,
                      transform: isSelected ? 'scale(1.05)' : 'scale(1)',
                    }}
                  >
                    <img src={avatar.file} alt={avatar.name} className="w-full h-full object-cover" />
                  </button>
                );
              })}
            </div>
            {editAvatar && (
              <p className="mt-2 text-xs text-slate-400 italic">
                {AVATARS.find(a => a.id === editAvatar)?.name} — "{AVATARS.find(a => a.id === editAvatar)?.description}"
              </p>
            )}
          </div>
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={handleSave}
              disabled={isUpdating}
              className="px-4 py-2 text-sm font-medium rounded-lg text-white disabled:opacity-50 transition-opacity hover:opacity-90"
              style={{ background: 'var(--cw-accent)' }}
            >
              {isUpdating ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => setEditMode(false)}
              className="px-4 py-2 text-sm font-medium rounded-lg border transition-all hover:opacity-80"
              style={{ borderColor: 'var(--cw-border)', color: isDark ? '#94a3b8' : '#6b7280' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Stat cards */}
      {statsLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl h-20 animate-pulse" style={{ background: 'var(--cw-surface)' }} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total Rated', value: stats?.total ?? 0, color: 'var(--cw-accent)', filter: 'all' },
            { label: 'Liked', value: stats?.liked ?? 0, color: '#4ade80', filter: 'liked' },
            { label: 'Skipped', value: stats?.disliked ?? 0, color: '#f87171', filter: 'disliked' },
            {
              label: 'Avg. Watch',
              value: stats?.avg_completion != null ? `${Math.round(stats.avg_completion * 100)}%` : '—',
              color: '#fbbf24',
              filter: 'watched',
            },
          ].map((stat) => (
            <Link
              key={stat.label}
              to={`/history?filter=${stat.filter}`}
              className="rounded-xl border p-4 flex flex-col gap-1 transition-opacity hover:opacity-80"
              style={{
                background: 'var(--cw-surface)',
                borderColor: 'var(--cw-border)',
                borderTopColor: stat.color,
                borderTopWidth: '2px',
              }}
            >
              <p className="text-2xl font-black" style={{ color: stat.color }}>{stat.value}</p>
              <p className="text-xs text-slate-400">{stat.label}</p>
            </Link>
          ))}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-6 mb-6">
        {/* Taste profile chart */}
        <div
          className="rounded-2xl border p-6"
          style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
        >
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-4">Your Taste Profile</h2>
          {statsLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="w-32 h-32 rounded-full animate-pulse" style={{ background: 'var(--cw-surface-elevated)' }} />
            </div>
          ) : stats && Object.keys(stats.genre_counts).length > 0 ? (
            <TasteProfileChart genreCounts={stats.genre_counts} likedCount={stats.liked} size={160} />
          ) : (
            <div className="text-center py-8 text-slate-500 text-sm">
              Rate at least 3 movies to see your taste profile
            </div>
          )}
        </div>

        {/* Personalization progress */}
        <div
          className="rounded-2xl border p-6 flex flex-col gap-4"
          style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
        >
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest">Personalization Level</h2>
          <div>
            <div className="flex items-end justify-between mb-1">
              <span className="text-3xl font-black" style={{ color: 'var(--cw-accent)' }}>
                {interactionCount}
                <span className="text-base text-slate-500 font-normal">/{CF_THRESHOLD}</span>
              </span>
              <span className="text-xs text-slate-400">interactions</span>
            </div>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--cw-surface-elevated)' }}>
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${personalizationPct}%`, background: 'var(--cw-accent)' }}
              />
            </div>
            <p className="text-xs text-slate-400 mt-2">
              {interactionCount >= CF_THRESHOLD
                ? '✓ Collaborative filtering is fully active — recommendations are personalized to you.'
                : `Rate ${CF_THRESHOLD - interactionCount} more movie${CF_THRESHOLD - interactionCount === 1 ? '' : 's'} to activate collaborative filtering.`}
            </p>
          </div>

          <div className="mt-auto pt-2 border-t" style={{ borderColor: 'var(--cw-border)' }}>
            <p className="text-xs text-slate-500 leading-relaxed">
              Cinewise combines <strong className="text-slate-400">semantic embeddings</strong> (content similarity) with <strong className="text-slate-400">SVD collaborative filtering</strong> (community patterns). The blend shifts from content-only to hybrid as you rate more films.
            </p>
          </div>
        </div>
      </div>

      {/* Recent activity */}
      {recentActivity.length > 0 && (
        <div
          className="rounded-2xl border p-6"
          style={{ background: 'var(--cw-surface)', borderColor: 'var(--cw-border)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest">Recent Activity</h2>
            <Link to="/history" className="text-xs font-medium hover:underline" style={{ color: 'var(--cw-accent)' }}>
              View all
            </Link>
          </div>
          <div className="flex flex-col gap-3">
            {recentActivity.map((item) => (
              <div key={item.movie_id} className="flex items-center gap-3">
                <div className="w-10 h-14 rounded-lg overflow-hidden flex-shrink-0" style={{ background: 'var(--cw-surface-elevated)' }}>
                  {item.poster_path && (
                    <img src={`${TMDB_POSTER_BASE}${item.poster_path}`} alt={item.title} className="w-full h-full object-cover" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{item.title}</p>
                  <p className="text-xs text-slate-500">{item.year ?? ''}</p>
                </div>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
                  item.action === 'like'
                    ? 'border-green-500/30 text-green-400 bg-green-500/10'
                    : 'border-red-500/30 text-red-400 bg-red-500/10'
                }`}>
                  {item.action === 'like' ? 'Liked' : 'Skipped'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfilePage;

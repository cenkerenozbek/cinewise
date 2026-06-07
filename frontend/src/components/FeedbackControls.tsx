import type { FeedbackAction } from '../lib/types';
import type { WatchCompletion } from '../lib/types';
import { WATCH_COMPLETION_VALUES } from '../lib/types';
import { WatchCompletionPicker } from './WatchCompletionPicker';

interface FeedbackControlsProps {
  title: string;
  vote?: FeedbackAction;
  onVote: (action: FeedbackAction) => void;
  watchCompletion?: WatchCompletion | null;
  onWatchCompletion?: (v: WatchCompletion) => void;
}

export function FeedbackControls({
  title,
  vote,
  onVote,
  watchCompletion,
  onWatchCompletion,
}: FeedbackControlsProps) {
  return (
    <div
      className="rounded-xl border p-3"
      style={{ background: 'var(--cw-surface-elevated)', borderColor: 'var(--cw-border)' }}
    >
      <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
        Rate this film
      </p>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onVote('like')}
          className={`flex h-9 items-center justify-center gap-1.5 rounded-lg border text-xs font-bold transition-all duration-200 ${
            vote === 'like'
              ? 'border-green-500 bg-green-500/20 text-green-300'
              : 'border-white/10 bg-transparent text-slate-400 hover:border-green-500/50 hover:text-green-400'
          }`}
          aria-label={`Like ${title}`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
            <path d="M1 8.998a1 1 0 0 1 1-1h3v9H2a1 1 0 0 1-1-1v-7Zm5.5 8.5h7.168a2 2 0 0 0 1.94-1.516l1.333-5.333A2 2 0 0 0 15 7.498H11V3.498a1.5 1.5 0 0 0-1.5-1.5.5.5 0 0 0-.462.31L6.5 8.498v9Z" />
          </svg>
          Like
        </button>
        <button
          type="button"
          onClick={() => onVote('dislike')}
          className={`flex h-9 items-center justify-center gap-1.5 rounded-lg border text-xs font-bold transition-all duration-200 ${
            vote === 'dislike'
              ? 'border-red-500 bg-red-500/20 text-red-300'
              : 'border-white/10 bg-transparent text-slate-400 hover:border-red-500/50 hover:text-red-400'
          }`}
          aria-label={`Mark ${title} as not for me`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
            <path d="M19 11.002a1 1 0 0 1-1 1h-3v-9h3a1 1 0 0 1 1 1v7Zm-5.5-8.5H6.332a2 2 0 0 0-1.94 1.516L3.06 9.351a2 2 0 0 0 1.94 2.484H9v3.5a1.5 1.5 0 0 0 1.5 1.5.5.5 0 0 0 .462-.31l2.538-6.023v-9Z" />
          </svg>
          Skip
        </button>
      </div>

      {/* Watch completion picker - appears after voting */}
      {vote && onWatchCompletion && (
        <div className="mt-3 overflow-hidden" style={{ animation: 'fadeInUp 0.3s ease both' }}>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
            How much did you watch?
          </p>
          <WatchCompletionPicker
            value={watchCompletion ?? null}
            onChange={(v) => {
              onWatchCompletion(v);
            }}
            accentColor="var(--cw-accent)"
          />
          {watchCompletion && (
            <p className="text-[10px] text-slate-500 mt-1">
              Saved: {Math.round(WATCH_COMPLETION_VALUES[watchCompletion] * 100)}% watched
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default FeedbackControls;

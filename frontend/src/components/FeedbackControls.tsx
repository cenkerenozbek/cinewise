import type { FeedbackAction } from '../lib/types';
import type { WatchCompletion } from '../lib/types';
import { WATCH_COMPLETION_VALUES } from '../lib/types';
import { WatchCompletionPicker } from './WatchCompletionPicker';

interface FeedbackControlsProps {
  title: string;
  vote?: FeedbackAction;
  onVote: (action: FeedbackAction) => void;
  onClearVote?: () => void;
  watchCompletion?: WatchCompletion | null;
  onWatchCompletion?: (v: WatchCompletion | null) => void;
}

export function FeedbackControls({
  title,
  vote,
  onVote,
  onClearVote,
  watchCompletion,
  onWatchCompletion,
}: FeedbackControlsProps) {
  function handleClick(action: FeedbackAction) {
    if (vote === action) {
      onClearVote?.();
    } else {
      onVote(action);
    }
  }

  return (
    <div className="mt-6 pt-5 border-t" style={{ borderColor: 'var(--cw-border)' }}>
      <p className="mb-3 text-xs font-semibold text-slate-400">Seen it?</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => handleClick('like')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all duration-200 ${
            vote === 'like'
              ? 'border-green-500 bg-green-500/20 text-green-300'
              : 'border-white/10 bg-transparent text-slate-400 hover:border-green-500/50 hover:text-green-400'
          }`}
          aria-label={vote === 'like' ? `Remove like from ${title}` : `Like ${title}`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
          </svg>
          Like
        </button>
        <button
          type="button"
          onClick={() => handleClick('dislike')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all duration-200 ${
            vote === 'dislike'
              ? 'border-red-500 bg-red-500/20 text-red-300'
              : 'border-white/10 bg-transparent text-slate-400 hover:border-red-500/50 hover:text-red-400'
          }`}
          aria-label={vote === 'dislike' ? `Remove dislike from ${title}` : `Mark ${title} as not for me`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
          </svg>
          Dislike
        </button>
      </div>

      {/* Watch completion picker - appears after voting */}
      {vote && onWatchCompletion && (
        <div className="mt-4 overflow-hidden" style={{ animation: 'fadeInUp 0.3s ease both' }}>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
            How much did you watch?
          </p>
          <WatchCompletionPicker
            value={watchCompletion ?? null}
            onChange={(v) => { onWatchCompletion(v); }}
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

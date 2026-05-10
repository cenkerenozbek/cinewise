import type { FeedbackAction } from '../lib/types';

interface FeedbackControlsProps {
  title: string;
  vote?: FeedbackAction;
  onVote: (action: FeedbackAction) => void;
}

export function FeedbackControls({ title, vote, onVote }: FeedbackControlsProps) {
  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-2">
      <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-gray-500">
        Feedback
      </p>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onVote('like')}
          className={`flex h-10 items-center justify-center gap-1.5 rounded-md border text-xs font-bold transition-colors ${
            vote === 'like'
              ? 'border-green-500 bg-green-600 text-white'
              : 'border-green-200 bg-white text-green-700 hover:bg-green-50'
          }`}
          aria-label={`Like ${title}`}
          title="Like"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path d="M1 8.998a1 1 0 0 1 1-1h3v9H2a1 1 0 0 1-1-1v-7Zm5.5 8.5h7.168a2 2 0 0 0 1.94-1.516l1.333-5.333A2 2 0 0 0 15 7.498H11V3.498a1.5 1.5 0 0 0-1.5-1.5.5.5 0 0 0-.462.31L6.5 8.498v9Z" />
          </svg>
          Like
        </button>
        <button
          type="button"
          onClick={() => onVote('dislike')}
          className={`flex h-10 items-center justify-center gap-1.5 rounded-md border text-xs font-bold transition-colors ${
            vote === 'dislike'
              ? 'border-red-500 bg-red-600 text-white'
              : 'border-red-200 bg-white text-red-700 hover:bg-red-50'
          }`}
          aria-label={`Mark ${title} as not for me`}
          title="Not for me"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path d="M19 11.002a1 1 0 0 1-1 1h-3v-9h3a1 1 0 0 1 1 1v7Zm-5.5-8.5H6.332a2 2 0 0 0-1.94 1.516L3.06 9.351a2 2 0 0 0 1.94 2.484H9v3.5a1.5 1.5 0 0 0 1.5 1.5.5.5 0 0 0 .462-.31l2.538-6.023v-9Z" />
          </svg>
          Not for me
        </button>
      </div>
    </div>
  );
}

export default FeedbackControls;

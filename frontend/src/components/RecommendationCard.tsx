import { useState } from 'react';
import { MovieCard } from './MovieCard';
import { FeedbackControls } from './FeedbackControls';
import type { FeedbackAction, MovieSummary, RecommendationItem, WatchCompletion } from '../lib/types';
import { WATCH_COMPLETION_VALUES } from '../lib/types';
import { useFeedback } from '../hooks/useFeedback';

interface RecommendationCardProps {
  item: RecommendationItem;
  vote?: FeedbackAction;
  onVote?: (tmdbId: number, action: FeedbackAction) => void;
  showFeedback?: boolean;
}

function recommendationToMovieSummary(item: RecommendationItem): MovieSummary {
  return {
    tmdb_id: item.tmdb_id,
    title: item.title,
    title_tr: item.title_tr,
    year: item.year,
    genres: item.genres,
    poster_path: item.poster_path,
    rating: item.rating,
  };
}

export function RecommendationCard({
  item,
  vote,
  onVote,
  showFeedback = false,
}: RecommendationCardProps) {
  const feedbackEnabled = showFeedback && onVote;
  const [watchCompletion, setWatchCompletion] = useState<WatchCompletion | null>(null);
  const { mutate: submitFeedback } = useFeedback();

  function handleWatchCompletion(v: WatchCompletion) {
    setWatchCompletion(v);
    submitFeedback({
      movie_id: item.tmdb_id,
      action: vote ?? 'like',
      watch_completion: WATCH_COMPLETION_VALUES[v],
    });
  }

  return (
    <div className="flex min-w-0 flex-col">
      <MovieCard movie={recommendationToMovieSummary(item)} />
      <div className="flex flex-1 flex-col gap-2 pt-2">
        <p className="text-xs leading-5 text-slate-400 italic">{item.explanation}</p>
        {item.overview && (
          <p className="text-xs leading-5 text-slate-500 line-clamp-3">{item.overview}</p>
        )}
        {feedbackEnabled && (
          <div className="mt-auto">
            <FeedbackControls
              title={item.title}
              vote={vote}
              onVote={(action) => onVote(item.tmdb_id, action)}
              watchCompletion={watchCompletion}
              onWatchCompletion={handleWatchCompletion}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default RecommendationCard;

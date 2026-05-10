import { MovieCard } from './MovieCard';
import { FeedbackControls } from './FeedbackControls';
import type { FeedbackAction, MovieSummary, RecommendationItem } from '../lib/types';

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

  return (
    <div className="flex min-w-0 flex-col">
      <MovieCard movie={recommendationToMovieSummary(item)} />
      <div className="flex flex-1 flex-col gap-3 pt-2">
        <p className="text-xs leading-5 text-gray-600">{item.explanation}</p>
        {item.overview && (
          <p className="text-xs leading-5 text-gray-500 line-clamp-3">{item.overview}</p>
        )}
        {feedbackEnabled && (
          <div className="mt-auto">
            <FeedbackControls
              title={item.title}
              vote={vote}
              onVote={(action) => onVote(item.tmdb_id, action)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default RecommendationCard;

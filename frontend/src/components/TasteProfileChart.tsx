import { useMoodTheme } from '../features/mood/MoodThemeContext';

const CHART_COLORS = [
  '#f59e0b', // amber - Happy
  '#2dd4bf', // teal - Tense
  '#b8a4ed', // lavender - Relaxing
  '#fb7185', // rose - Romantic
  '#a855f7', // purple - Mind-bending
  '#6366f1', // indigo - default
  '#34d399', // emerald
  '#f97316', // orange
  '#60a5fa', // blue
  '#e879f9', // fuchsia
  '#fbbf24', // yellow
  '#4ade80', // green
];

interface TasteProfileChartProps {
  genreCounts: Record<string, number>;
  likedCount?: number;
  size?: number;
}

export function TasteProfileChart({ genreCounts, likedCount, size = 180 }: TasteProfileChartProps) {
  const { isDark } = useMoodTheme();
  const totalTextColor = isDark ? '#f1f5f9' : '#111827';
  const entries = Object.entries(genreCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8);

  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
        No data yet
      </div>
    );
  }

  // Build arc paths for SVG donut
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const innerR = size * 0.22;
  const gap = 0.03; // radians gap between arcs

  // Pre-compute cumulative start angles to avoid mutating a variable inside map.
  const startAngles = entries.reduce<number[]>((acc, [, count]) => {
    const prev = acc.length > 0 ? acc[acc.length - 1] : -Math.PI / 2;
    const frac = count / total;
    acc.push(prev + frac * 2 * Math.PI);
    return acc;
  }, []);

  const arcs = entries.map(([genre, count], i) => {
    const fraction = count / total;
    const base = i === 0 ? -Math.PI / 2 : startAngles[i - 1];
    const startAngle = base + gap / 2;
    const endAngle = base + fraction * 2 * Math.PI - gap / 2;

    const x1 = cx + r * Math.cos(startAngle);
    const y1 = cy + r * Math.sin(startAngle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const ix1 = cx + innerR * Math.cos(endAngle);
    const iy1 = cy + innerR * Math.sin(endAngle);
    const ix2 = cx + innerR * Math.cos(startAngle);
    const iy2 = cy + innerR * Math.sin(startAngle);

    const largeArc = fraction * 2 * Math.PI - gap > Math.PI ? 1 : 0;

    const d = [
      `M ${x1} ${y1}`,
      `A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`,
      `L ${ix1} ${iy1}`,
      `A ${innerR} ${innerR} 0 ${largeArc} 0 ${ix2} ${iy2}`,
      'Z',
    ].join(' ');

    return { d, color: CHART_COLORS[i % CHART_COLORS.length], genre, count };
  });

  return (
    <div className="flex flex-col items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {arcs.map((arc) => (
          <path key={arc.genre} d={arc.d} fill={arc.color} opacity={0.9}>
            <title>{arc.genre}: {arc.count}</title>
          </path>
        ))}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.13}
          fontWeight="700"
          fill={totalTextColor}
        >
          {likedCount ?? total}
        </text>
        <text
          x={cx}
          y={cy + size * 0.1}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.072}
          fill="#94a3b8"
        >
          liked
        </text>
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 justify-center max-w-xs">
        {arcs.map((arc) => (
          <div key={arc.genre} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: arc.color }} />
            <span className="text-xs text-slate-400">{arc.genre}</span>
            <span className="text-xs font-bold" style={{ color: arc.color }}>{arc.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default TasteProfileChart;

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="relative flex-1">
      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 105 11a6 6 0 0012 0z" />
        </svg>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search movies..."
        className="w-full pl-10 pr-4 py-2.5 rounded-xl border text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all"
        style={{
          background: 'var(--cw-surface)',
          borderColor: 'var(--cw-border)',
        }}
      />
    </div>
  );
}

export default SearchBar;

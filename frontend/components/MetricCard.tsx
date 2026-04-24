interface MetricCardProps {
  label: string;
  value: string | number;
  color: 'accent' | 'trusted' | 'flagged' | 'quarantined';
  sub?: string;
  trend?: 'up' | 'down' | 'flat';
}

const colorMap = {
  accent:      { text: 'text-accent',      bg: 'rgba(88,166,255,.08)',    border: 'rgba(88,166,255,.2)',   glow: 'shadow-accent' },
  trusted:     { text: 'text-trusted',     bg: 'rgba(35,134,54,.08)',     border: 'rgba(35,134,54,.25)',   glow: 'shadow-trusted' },
  flagged:     { text: 'text-flagged',     bg: 'rgba(210,153,34,.08)',    border: 'rgba(210,153,34,.25)',  glow: 'shadow-flagged' },
  quarantined: { text: 'text-quarantined', bg: 'rgba(218,54,51,.08)',     border: 'rgba(218,54,51,.25)',   glow: 'shadow-quarantined' },
};

const trendIcon = { up: '↑', down: '↓', flat: '→' };
const trendColor = { up: 'text-trusted', down: 'text-quarantined', flat: 'text-muted' };

export function MetricCard({ label, value, color, sub, trend }: MetricCardProps) {
  const c = colorMap[color];
  return (
    <div
      className="bg-surface border rounded-2xl p-5 text-center card-hover animate-fade-in-up"
      style={{ borderColor: c.border, background: `linear-gradient(160deg, ${c.bg} 0%, rgba(22,27,34,.9) 100%)` }}
    >
      <div className="text-[11px] text-muted uppercase tracking-[.08em] font-medium">{label}</div>
      <div className={`text-3xl font-extrabold mt-2 animate-count-up tabular-nums ${c.text}`}>{value}</div>
      {(sub || trend) && (
        <div className="flex items-center justify-center gap-1 mt-1.5 text-[11px]">
          {trend && <span className={trendColor[trend]}>{trendIcon[trend]}</span>}
          {sub && <span className="text-muted">{sub}</span>}
        </div>
      )}
    </div>
  );
}

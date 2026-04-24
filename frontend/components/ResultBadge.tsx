interface ResultBadgeProps {
  decision: string;
  score: number;
  size?: 'sm' | 'md';
}

const cfg: Record<string, { bg: string; text: string; border: string; dot: string; icon: string }> = {
  trusted:     { bg: 'rgba(35,134,54,.12)',  text: '#3fb950', border: 'rgba(35,134,54,.35)',  dot: '#238636', icon: '✓' },
  flagged:     { bg: 'rgba(210,153,34,.12)', text: '#e3b341', border: 'rgba(210,153,34,.35)', dot: '#d29922', icon: '!' },
  quarantined: { bg: 'rgba(218,54,51,.12)',  text: '#f85149', border: 'rgba(218,54,51,.35)',  dot: '#da3633', icon: '✕' },
};

export function ResultBadge({ decision, score, size = 'md' }: ResultBadgeProps) {
  const c  = cfg[decision] || cfg.quarantined;
  const sm = size === 'sm';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold tabular-nums ${sm ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'}`}
      style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
    >
      <span style={{ color: c.dot, fontSize: sm ? 9 : 10, lineHeight: 1 }}>{c.icon}</span>
      {decision?.toUpperCase()}
      {typeof score === 'number' && !sm && (
        <span style={{ opacity: .65 }}>{score.toFixed(2)}</span>
      )}
    </span>
  );
}

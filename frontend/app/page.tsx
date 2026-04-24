'use client';

import { useState, useEffect } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { ResultBadge } from '@/components/ResultBadge';
import { api } from '@/lib/api';

// Mini confidence bar
function ConfBar({ score, decision }: { score: number; decision: string }) {
  const colors: Record<string, string> = {
    trusted: '#238636', flagged: '#d29922', quarantined: '#da3633',
  };
  const c = colors[decision] || '#8b949e';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: '#30363d' }}>
        <div className="h-1.5 rounded-full animate-fill-bar"
          style={{ width: `${(score || 0) * 100}%`, background: c, transition: 'width .5s ease' }} />
      </div>
      <span className="font-mono text-xs tabular-nums" style={{ color: c, minWidth: 32 }}>
        {typeof score === 'number' ? score.toFixed(2) : '—'}
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const d = data || {
    total_validations: 0, trusted: 0, flagged: 0, quarantined: 0,
    avg_confidence: 0, total_batches: 0, total_violations: 0,
    top_violated_rules: [], recent_activity: [], by_domain: [],
  };

  const passRate = d.total_validations > 0
    ? Math.round((d.trusted / d.total_validations) * 100) : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted mt-0.5">Real-time validation telemetry · all domains</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted px-3 py-1.5 rounded-lg"
          style={{ background: '#1c2129', border: '1px solid #30363d' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-trusted animate-pulse-slow" />
          Live
        </div>
      </div>

      {/* Metric row */}
      {loading ? (
        <div className="grid grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-5 gap-4 stagger">
          <MetricCard label="Total Validations" value={d.total_validations} color="accent"
            sub={d.total_validations > 0 ? 'all time' : 'run one to start'} />
          <MetricCard label="Trusted" value={d.trusted} color="trusted"
            sub={passRate > 0 ? `${passRate}% pass rate` : undefined} />
          <MetricCard label="Flagged" value={d.flagged} color="flagged" />
          <MetricCard label="Quarantined" value={d.quarantined} color="quarantined" />
          <MetricCard label="Avg Confidence" value={d.avg_confidence?.toFixed(2) || '—'} color="accent"
            sub="0 = quarantined · 1 = perfect" />
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-5 gap-6">

        {/* Recent activity — 3 cols */}
        <div className="col-span-3 space-y-3">
          <h2 className="text-base font-semibold text-white">Recent Activity</h2>
          {loading ? (
            <div className="skeleton h-48 rounded-xl" />
          ) : d.recent_activity?.length > 0 ? (
            <div className="rounded-xl overflow-hidden" style={{ background: '#161b22', border: '1px solid #30363d' }}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b" style={{ borderColor: '#21262d' }}>
                    {['Record', 'Domain', 'Confidence', 'Decision'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-[10px] text-muted uppercase tracking-[.08em] font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {d.recent_activity.map((r: any, i: number) => (
                    <tr key={i}
                      className="border-b transition hover:bg-white/[.03] animate-fade-in-up"
                      style={{ borderColor: '#21262d', animationDelay: `${i * .04}s` }}>
                      <td className="px-4 py-3 font-mono text-xs text-white">{r.record_id}</td>
                      <td className="px-4 py-3 text-xs text-muted">{r.domain?.replace(/_/g, ' ')}</td>
                      <td className="px-4 py-3 w-36"><ConfBar score={r.confidence_score} decision={r.decision} /></td>
                      <td className="px-4 py-3"><ResultBadge decision={r.decision} score={r.confidence_score} size="sm" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl p-14 text-center" style={{ background: '#161b22', border: '2px dashed #30363d' }}>
              <div className="text-3xl mb-3 opacity-20">◈</div>
              <p className="text-sm text-muted">No validations yet.</p>
              <p className="text-xs text-muted/60 mt-1">
                Go to <a href="/validate" className="text-accent hover:underline">Validate</a> to get started.
              </p>
            </div>
          )}
        </div>

        {/* Right column — 2 cols */}
        <div className="col-span-2 space-y-4">

          {/* Top violated rules */}
          <div className="rounded-xl p-4 space-y-3" style={{ background: '#161b22', border: '1px solid #30363d' }}>
            <h2 className="text-sm font-semibold text-white">Top Failing Rules</h2>
            {loading ? <div className="skeleton h-24 rounded-lg" /> :
            d.top_violated_rules?.length > 0 ? (
              d.top_violated_rules.map((r: any, i: number) => {
                const maxCount = d.top_violated_rules[0]?.count || 1;
                const pct = (r.count / maxCount) * 100;
                return (
                  <div key={i} className="space-y-1 animate-fade-in-up" style={{ animationDelay: `${i*.06}s` }}>
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${r.severity === 'critical' ? 'bg-quarantined' : 'bg-flagged'}`} />
                        <span className="font-mono font-semibold text-white">{r.rule_id}</span>
                      </div>
                      <span className="text-muted tabular-nums">{r.count}</span>
                    </div>
                    <div className="h-1 rounded-full" style={{ background: '#21262d' }}>
                      <div className="h-1 rounded-full"
                        style={{ width: `${pct}%`, background: r.severity === 'critical' ? '#da3633' : '#d29922',
                                 transition: 'width .6s ease' }} />
                    </div>
                  </div>
                );
              })
            ) : <p className="text-xs text-muted text-center py-3">No violations recorded</p>}
          </div>

          {/* Domain breakdown */}
          <div className="rounded-xl p-4" style={{ background: '#161b22', border: '1px solid #30363d' }}>
            <h2 className="text-sm font-semibold text-white mb-3">By Domain</h2>
            {loading ? <div className="skeleton h-16 rounded-lg" /> :
            d.by_domain?.length > 0 ? (
              d.by_domain.map((dom: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 text-xs border-b last:border-0"
                  style={{ borderColor: '#21262d' }}>
                  <span className="text-text/80">{dom.domain?.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-muted tabular-nums">{dom.count} records</span>
                    <span className="font-mono text-accent tabular-nums">{dom.avg_confidence?.toFixed(2)}</span>
                  </div>
                </div>
              ))
            ) : <p className="text-xs text-muted text-center py-3">No data</p>}
          </div>

          {/* Misc stats */}
          <div className="rounded-xl p-4" style={{ background: '#161b22', border: '1px solid #30363d' }}>
            {[
              ['Total Batches',    d.total_batches],
              ['Rule Violations',  d.total_violations],
            ].map(([l, v]: any) => (
              <div key={l} className="flex justify-between py-2 text-xs border-b last:border-0"
                style={{ borderColor: '#21262d' }}>
                <span className="text-muted">{l}</span>
                <span className="font-semibold text-white tabular-nums">{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

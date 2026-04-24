'use client';

import { useState, useEffect } from 'react';
import { ResultBadge } from '@/components/ResultBadge';
import { api } from '@/lib/api';

function ConfBar({ score, decision }: { score: number; decision: string }) {
  const c: Record<string, string> = { trusted: '#238636', flagged: '#d29922', quarantined: '#da3633' };
  const col = c[decision] || '#8b949e';
  return (
    <div className="flex items-center gap-2 w-24">
      <div className="flex-1 h-1 rounded-full" style={{ background: '#30363d' }}>
        <div className="h-1 rounded-full" style={{ width: `${(score || 0) * 100}%`, background: col }} />
      </div>
      <span className="font-mono text-[11px] tabular-nums" style={{ color: col }}>
        {typeof score === 'number' ? score.toFixed(2) : '—'}
      </span>
    </div>
  );
}

export default function AuditPage() {
  const [entries,        setEntries]        = useState<any[]>([]);
  const [loading,        setLoading]        = useState(true);
  const [domainFilter,   setDomainFilter]   = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [expanded,       setExpanded]       = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api.auditLogs(100, domainFilter || undefined, decisionFilter || undefined)
      .then((d: any) => setEntries(d.entries || []))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [domainFilter, decisionFilter]);

  const counts = {
    trusted:     entries.filter(e => e.decision === 'trusted').length,
    flagged:     entries.filter(e => e.decision === 'flagged').length,
    quarantined: entries.filter(e => e.decision === 'quarantined').length,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Audit Trail</h1>
        <p className="text-sm text-muted mt-0.5">Complete validation history · click a row to expand</p>
      </div>

      {/* Summary chips */}
      {entries.length > 0 && (
        <div className="flex gap-3">
          {[
            { label: 'Trusted',     val: counts.trusted,     bg: 'rgba(35,134,54,.1)',  c: '#3fb950', b: 'rgba(35,134,54,.25)'  },
            { label: 'Flagged',     val: counts.flagged,     bg: 'rgba(210,153,34,.1)', c: '#e3b341', b: 'rgba(210,153,34,.25)' },
            { label: 'Quarantined', val: counts.quarantined, bg: 'rgba(218,54,51,.1)',  c: '#f85149', b: 'rgba(218,54,51,.25)'  },
          ].map(s => (
            <div key={s.label} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold"
              style={{ background: s.bg, color: s.c, border: `1px solid ${s.b}` }}>
              <span className="tabular-nums font-bold">{s.val}</span> {s.label}
            </div>
          ))}
          <div className="flex-1" />
          <span className="text-xs text-muted self-center tabular-nums">{entries.length} records</span>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        {[
          { val: domainFilter, set: setDomainFilter, opts: [['','All Domains'],['healthcare_intake','Healthcare'],['financial_loan_application','Finance']] },
          { val: decisionFilter, set: setDecisionFilter, opts: [['','All Decisions'],['trusted','Trusted'],['flagged','Flagged'],['quarantined','Quarantined']] },
        ].map((f, i) => (
          <select key={i} value={f.val} onChange={e => f.set(e.target.value)}
            className="text-sm rounded-lg px-3 py-2"
            style={{ background: '#1c2129', border: '1px solid #30363d', color: '#c9d1d9' }}>
            {f.opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2">{[...Array(5)].map((_,i) => <div key={i} className="skeleton h-12 rounded-xl" />)}</div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl p-16 text-center" style={{ background: '#161b22', border: '2px dashed #30363d' }}>
          <div className="text-3xl mb-3 opacity-20">≡</div>
          <p className="text-sm text-muted">No audit records yet.</p>
          <p className="text-xs text-muted/60 mt-1">Run a validation to start building history.</p>
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden" style={{ background: '#161b22', border: '1px solid #30363d' }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: '#21262d' }}>
                {['Record ID', 'Domain', 'Structural', 'Semantic', 'Confidence', 'Decision', 'Violations'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[10px] text-muted uppercase tracking-[.08em] font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((r, i) => {
                const isOpen = expanded === `${r.record_id}-${i}`;
                const key    = `${r.record_id}-${i}`;
                const viols  = r.violated_rules || r.violations || [];
                return [
                  <tr key={key}
                    className="border-b cursor-pointer transition hover:bg-white/[.025] animate-fade-in-up"
                    style={{ borderColor: '#21262d', animationDelay: `${Math.min(i,.15) * .03}s` }}
                    onClick={() => setExpanded(isOpen ? null : key)}>
                    <td className="px-4 py-3 font-mono text-xs text-white">{r.record_id}</td>
                    <td className="px-4 py-3 text-xs text-muted">{r.domain?.replace(/_/g,' ')}</td>
                    <td className="px-4 py-3 text-center text-sm">{r.structural_valid ? '✓' : '✕'}</td>
                    <td className="px-4 py-3 text-center text-sm">{r.semantic_valid   ? '✓' : '✕'}</td>
                    <td className="px-4 py-3"><ConfBar score={r.confidence_score} decision={r.decision} /></td>
                    <td className="px-4 py-3"><ResultBadge decision={r.decision} score={r.confidence_score} size="sm" /></td>
                    <td className="px-4 py-3">
                      {viols.length > 0
                        ? <div className="flex gap-1 flex-wrap">
                            {viols.slice(0,3).map((v: any) => (
                              <span key={v.rule_id||v} className="tag"
                                style={{ background:'rgba(218,54,51,.1)', color:'#f85149', border:'1px solid rgba(218,54,51,.2)' }}>
                                {v.rule_id || v}
                              </span>
                            ))}
                            {viols.length > 3 && <span className="text-[10px] text-muted">+{viols.length-3}</span>}
                          </div>
                        : <span className="text-[10px] text-trusted/70">—</span>
                      }
                    </td>
                  </tr>,
                  isOpen && (
                    <tr key={`${key}-exp`} style={{ background: '#1c2129' }}>
                      <td colSpan={7} className="px-4 py-3 animate-fade-in">
                        <div className="text-xs text-muted/80 leading-relaxed">
                          <span className="font-semibold text-text/60">Explanation: </span>
                          {r.explanation || 'No explanation recorded.'}
                        </div>
                      </td>
                    </tr>
                  ),
                ];
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

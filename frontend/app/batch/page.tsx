'use client';

import { useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { ResultBadge } from '@/components/ResultBadge';
import { api } from '@/lib/api';

const PLACEHOLDER = `[
  {
    "patient_id": "P-10045",
    "date_of_birth": "1978-11-02",
    "admission_date": "2024-09-14",
    "discharge_date": "2024-09-19",
    "diagnosis_code": "J18.9",
    "medication": "Azithromycin",
    "patient_age": 45,
    "emergency_admission": false
  }
]`;

function downloadJSON(data: any, filename: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  a.download = filename; a.click();
}

function ConfBar({ score, decision }: { score: number; decision: string }) {
  const c: Record<string, string> = { trusted: '#238636', flagged: '#d29922', quarantined: '#da3633' };
  const col = c[decision] || '#8b949e';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 rounded-full" style={{ background: '#30363d' }}>
        <div className="h-1.5 rounded-full" style={{ width: `${(score || 0) * 100}%`, background: col }} />
      </div>
      <span className="font-mono text-xs tabular-nums" style={{ color: col, minWidth: 28 }}>
        {typeof score === 'number' ? score.toFixed(2) : '—'}
      </span>
    </div>
  );
}

export default function BatchPage() {
  const [domain,  setDomain]  = useState('healthcare');
  const [json,    setJson]    = useState('');
  const [result,  setResult]  = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  const run = async () => {
    setLoading(true); setResult(null); setError('');
    try {
      const records = JSON.parse(json);
      if (!Array.isArray(records)) throw new Error('Input must be a JSON array');
      setResult(await api.batchValidate(domain, records));
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const s     = result?.summary || {};
  const drift = result?.drift_summary;
  const total = result?.total_records || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Batch Validation</h1>
          <p className="text-sm text-muted mt-0.5">Process multiple records · includes drift detection</p>
        </div>
        {result && (
          <button onClick={() => downloadJSON(result, `sg-batch-${result.batch_id || 'result'}.json`)}
            className="text-xs text-muted hover:text-text border border-border rounded-lg px-3 py-2 transition">
            ⬇ Export JSON
          </button>
        )}
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 160px' }}>
        <textarea value={json} onChange={e => { setJson(e.target.value); setResult(null); setError(''); }}
          style={{ background: '#161b22', border: `1px solid ${json && !result ? '#3d444e' : '#30363d'}`,
                   borderRadius: 12, padding: 16, color: '#c9d1d9', fontFamily: 'monospace',
                   fontSize: 11, height: 160, resize: 'none', lineHeight: 1.6, width: '100%' }}
          placeholder={PLACEHOLDER} />
        <div className="flex flex-col gap-3">
          <select value={domain} onChange={e => setDomain(e.target.value)}
            style={{ background: '#1c2129', border: '1px solid #30363d', borderRadius: 8,
                     padding: '8px 10px', color: '#c9d1d9', fontSize: 13 }}>
            <option value="healthcare">🏥 Healthcare</option>
            <option value="finance">💰 Finance</option>
          </select>
          <button onClick={run} disabled={loading || !json.trim()}
            className="flex-1 font-semibold rounded-xl transition text-white text-sm"
            style={{ background: loading ? '#1c2129' : '#1f6feb',
                     border: '1px solid rgba(88,166,255,.3)',
                     opacity: !json.trim() ? .4 : 1 }}>
            {loading ? '⟳ Running…' : '📦 Run Batch'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(218,54,51,.08)', border: '1px solid rgba(218,54,51,.3)',
                      borderRadius: 12, padding: 14, color: '#f85149', fontSize: 13 }}>
          {error}
        </div>
      )}

      {!result && !error && (
        <div style={{ background: '#161b22', border: '2px dashed #30363d', borderRadius: 12,
                      padding: 40, textAlign: 'center', color: '#8b949e', fontSize: 13 }}>
          <div style={{ fontSize: 24, marginBottom: 8, opacity: .2 }}>⬡⬡</div>
          Paste a JSON array of records, then click <strong style={{ color: '#58a6ff' }}>Run Batch</strong>
        </div>
      )}

      {result && (
        <div className="space-y-4 animate-fade-in">
          <div className="grid grid-cols-5 gap-3 stagger">
            <MetricCard label="Total Records"  value={total}       color="accent"
              sub={total > 0 ? `${s.processing_time_ms?.toFixed(0)}ms` : undefined} />
            <MetricCard label="Trusted"        value={s.trusted}   color="trusted"
              sub={total > 0 ? `${Math.round((s.trusted / total) * 100)}%` : undefined} />
            <MetricCard label="Flagged"        value={s.flagged}   color="flagged" />
            <MetricCard label="Quarantined"    value={s.quarantined} color="quarantined" />
            <MetricCard label="Avg Confidence" value={s.mean_confidence?.toFixed(2) || '—'} color="accent" />
          </div>

          {drift?.drift_detected && (
            <div style={{ background: 'rgba(218,54,51,.06)', border: '1px solid rgba(218,54,51,.3)',
                          borderRadius: 12, padding: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f85149', marginBottom: 8 }}>
                ⚠ Drift Detected — {drift.alerts?.length} alert{drift.alerts?.length !== 1 ? 's' : ''}
              </h3>
              {drift.alerts?.map((a: any, i: number) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12, marginBottom: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, marginTop: 3,
                                  background: a.severity === 'high' ? '#da3633' : '#d29922' }} />
                  <span style={{ color: '#adbac7' }}>
                    <strong style={{ color: '#e3b341' }}>[{a.severity?.toUpperCase()}]</strong> {a.message}
                  </span>
                </div>
              ))}
            </div>
          )}

          {drift && !drift.drift_detected && (
            <div style={{ background: 'rgba(35,134,54,.05)', border: '1px solid rgba(35,134,54,.2)',
                          borderRadius: 10, padding: '10px 14px', fontSize: 12, color: 'rgba(63,185,80,.8)' }}>
              ✓ No distribution drift detected
            </div>
          )}

          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 12, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #21262d' }}>
                  {['Record ID', 'Domain', 'Confidence', 'Decision', 'Violations'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '10px 16px', fontSize: 10,
                                         color: '#8b949e', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600 }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.results?.map((r: any, i: number) => (
                  <tr key={i} className="animate-fade-in-up hover:bg-white/[.025] transition"
                    style={{ borderBottom: '1px solid #21262d', animationDelay: `${Math.min(i, 10) * .03}s` }}>
                    <td style={{ padding: '10px 16px', fontFamily: 'monospace', fontSize: 11, color: '#fff' }}>{r.record_id}</td>
                    <td style={{ padding: '10px 16px', fontSize: 11, color: '#8b949e' }}>{r.domain?.replace(/_/g, ' ')}</td>
                    <td style={{ padding: '10px 16px' }}><ConfBar score={r.confidence_score} decision={r.decision} /></td>
                    <td style={{ padding: '10px 16px' }}><ResultBadge decision={r.decision} score={r.confidence_score} size="sm" /></td>
                    <td style={{ padding: '10px 16px' }}>
                      {r.violated_rules?.length > 0
                        ? <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                            {r.violated_rules.map((v: any) => (
                              <span key={v.rule_id}
                                style={{ background: 'rgba(218,54,51,.1)', color: '#f85149',
                                         border: '1px solid rgba(218,54,51,.2)', padding: '1px 6px',
                                         borderRadius: 12, fontSize: 10, fontWeight: 600 }}>
                                {v.rule_id}
                              </span>
                            ))}
                          </div>
                        : <span style={{ fontSize: 10, color: 'rgba(63,185,80,.6)' }}>—</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

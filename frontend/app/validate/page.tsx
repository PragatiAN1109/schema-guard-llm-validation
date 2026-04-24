'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';

// ── constants ─────────────────────────────────────────────────────────────────

const DEC_CFG: Record<string, { bg: string; border: string; text: string; glow: string; icon: string; label: string }> = {
  trusted:     { bg: 'rgba(35,134,54,.14)',  border: 'rgba(35,134,54,.4)',   text: '#3fb950', glow: '0 0 32px rgba(35,134,54,.25)',  icon: '✓', label: 'TRUSTED' },
  flagged:     { bg: 'rgba(210,153,34,.14)', border: 'rgba(210,153,34,.4)',  text: '#e3b341', glow: '0 0 32px rgba(210,153,34,.25)', icon: '!', label: 'FLAGGED' },
  quarantined: { bg: 'rgba(218,54,51,.14)',  border: 'rgba(218,54,51,.4)',   text: '#f85149', glow: '0 0 32px rgba(218,54,51,.25)',  icon: '✕', label: 'QUARANTINED' },
};

const SEV_CFG: Record<string, { bg: string; border: string; text: string; barColor: string; leftBar: string }> = {
  critical: { bg: 'rgba(218,54,51,.07)',  border: 'rgba(218,54,51,.25)',  text: '#f85149', barColor: '#da3633', leftBar: '#da3633' },
  warning:  { bg: 'rgba(210,153,34,.07)', border: 'rgba(210,153,34,.25)', text: '#e3b341', barColor: '#d29922', leftBar: '#d29922' },
};

const CONF_CFG: Record<string, { bg: string; border: string; text: string; icon: string; label: string }> = {
  definite: { bg: 'rgba(35,134,54,.12)',  border: 'rgba(35,134,54,.3)',   text: '#3fb950', icon: '⚡', label: 'Auto-fix' },
  probable: { bg: 'rgba(210,153,34,.12)', border: 'rgba(210,153,34,.3)',  text: '#e3b341', icon: '⚠', label: 'Review advised' },
  manual:   { bg: 'rgba(218,54,51,.12)',  border: 'rgba(218,54,51,.3)',   text: '#f85149', icon: '🔍', label: 'Manual review' },
};

// Why-this-matters copy per rule
const WHY_MATTERS: Record<string, { impact: string; downstream: string }> = {
  'HC-001': {
    impact:     'Incorrect age causes wrong dosing thresholds, age-gated treatment decisions, and paediatric/adult misclassification.',
    downstream: 'Billing rejections under CMS age-edits, DRG miscalculation, quality-measure misattribution.',
  },
  'HC-002': {
    impact:     'A patient cannot be admitted before birth. This indicates a corrupted DOB or wrong year in admission date.',
    downstream: 'Full encounter invalidated for CMS billing; audit trigger for identity fraud review.',
  },
  'HC-003': {
    impact:     'Negative length-of-stay is clinically impossible and breaks DRG calculation.',
    downstream: 'UB-04 claim rejection, incorrect LOS metrics, and risk-adjustment failures.',
  },
  'HC-004': {
    impact:     'Age-restricted ICD-10 codes assigned to wrong age groups cause clinical decision errors.',
    downstream: 'CMS NCCI edit failure, claim denial, quality-measure exclusion.',
  },
  'HC-005': {
    impact:     'Medication-diagnosis mismatch may indicate a copy-paste error from a previous record or formulary confusion.',
    downstream: 'Pharmacy review flag, medication reconciliation failure, potential patient safety event.',
  },
  'FN-001': {
    impact:     'Temporal impossibility: a loan cannot be approved before it is applied for.',
    downstream: 'TILA-RESPA disclosure timeline violation; CFPB audit flag; loan ineligible for secondary market.',
  },
  'FN-002': {
    impact:     'Loan-to-income ratio far exceeds the 10× Ability-to-Repay limit.',
    downstream: 'Loan ineligible for QM safe-harbour; ATR violation exposure; GSE purchase rejection.',
  },
  'FN-003': {
    impact:     'Existing debt exceeds 60% of income before the new loan is factored in.',
    downstream: 'Fannie Mae DU rejection; elevated default risk flag; manual underwriter escalation required.',
  },
  'FN-004': {
    impact:     'Employment history longer than the applicant has been alive — data entry error or identity mismatch.',
    downstream: 'ATR income verification failure; potential mortgage fraud investigation trigger.',
  },
  'FN-005': {
    impact:     'Lender cannot approve more than requested without issuing a counter-offer disclosure.',
    downstream: 'Regulation B (ECOA) counter-offer violation; borrower notification requirement not met.',
  },
};

function downloadJSON(data: any, name: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  a.download = name; a.click();
}

// ── Confidence Arc SVG ────────────────────────────────────────────────────────
function ConfidenceArc({ score, decision }: { score: number; decision: string }) {
  const r = 52, cx = 68, cy = 68;
  const circumference = Math.PI * r; // half-circle
  const offset = circumference * (1 - score);
  const dc = DEC_CFG[decision] || DEC_CFG.quarantined;
  return (
    <svg width="136" height="80" viewBox="0 0 136 80" className="overflow-visible">
      {/* Track */}
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke="#30363d" strokeWidth="8" strokeLinecap="round" />
      {/* Fill */}
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke={dc.text} strokeWidth="8" strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        style={{ transition: 'stroke-dashoffset .7s cubic-bezier(.34,1.12,.64,1)', filter: `drop-shadow(0 0 6px ${dc.text})` }}
      />
      {/* Score label */}
      <text x={cx} y={cy - 8} textAnchor="middle" fill={dc.text}
        fontSize="22" fontWeight="800" fontFamily="monospace">{score.toFixed(2)}</text>
      <text x={cx} y={cy + 8} textAnchor="middle" fill="#8b949e"
        fontSize="9" fontWeight="600" letterSpacing="2">CONFIDENCE</text>
    </svg>
  );
}

// ── Rule violation card ───────────────────────────────────────────────────────
function ViolationCard({ v, idx }: { v: any; idx: number }) {
  const [expanded, setExpanded] = useState(false);
  const sc = SEV_CFG[v.severity] || SEV_CFG.warning;
  const why = WHY_MATTERS[v.rule_id];

  return (
    <div className="rounded-xl overflow-hidden animate-fade-in-up"
      style={{ animationDelay: `${idx * .07}s`, background: sc.bg, border: `1px solid ${sc.border}`, borderLeft: `3px solid ${sc.leftBar}` }}>
      <button className="w-full text-left p-4" onClick={() => setExpanded(x => !x)}>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-[10px] font-bold px-2 py-0.5 rounded-full"
            style={{ background: `${sc.barColor}22`, color: sc.text, border: `1px solid ${sc.border}` }}>
            {v.severity?.toUpperCase()}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-sm text-white">{v.rule_id}</span>
              <span className="text-[10px] text-muted font-mono">{v.rule_name}</span>
            </div>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: '#adbac7' }}>{v.message}</p>
          </div>
          <span className="text-muted text-xs mt-1 flex-shrink-0">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && why && (
        <div className="px-4 pb-4 pt-0 space-y-3 animate-fade-in border-t" style={{ borderColor: sc.border }}>
          <div className="mt-3 rounded-lg p-3" style={{ background: 'rgba(88,166,255,.05)', border: '1px solid rgba(88,166,255,.12)' }}>
            <div className="text-[10px] font-semibold text-accent uppercase tracking-[.08em] mb-1.5 flex items-center gap-1.5">
              <span>⚡</span> Why This Matters
            </div>
            <p className="text-xs text-text/80 leading-relaxed">{why.impact}</p>
          </div>
          <div className="rounded-lg p-3" style={{ background: 'rgba(218,54,51,.05)', border: '1px solid rgba(218,54,51,.12)' }}>
            <div className="text-[10px] font-semibold uppercase tracking-[.08em] mb-1.5" style={{ color: '#f85149' }}>
              ↳ Downstream Impact
            </div>
            <p className="text-xs leading-relaxed" style={{ color: '#adbac7' }}>{why.downstream}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Suggestions panel ─────────────────────────────────────────────────────────
function SuggestionsPanel({ suggestions }: { suggestions: any }) {
  return (
    <div className="space-y-3 animate-fade-in">
      {/* Summary */}
      <div className="rounded-xl p-4" style={{ background: 'rgba(88,166,255,.06)', border: '1px solid rgba(88,166,255,.15)' }}>
        <p className="text-sm text-text/80 leading-relaxed mb-3">{suggestions.summary}</p>
        <div className="flex gap-2 flex-wrap">
          <span className="tag" style={{ background: 'rgba(35,134,54,.15)', color: '#3fb950', border: '1px solid rgba(35,134,54,.3)' }}>
            ⚡ {suggestions.total_fixable} auto-fixable
          </span>
          <span className="tag" style={{ background: 'rgba(218,54,51,.15)', color: '#f85149', border: '1px solid rgba(218,54,51,.3)' }}>
            🔍 {suggestions.total_manual} manual review
          </span>
        </div>
      </div>

      {suggestions.suggestions.map((s: any, i: number) => {
        const cc = CONF_CFG[s.confidence] || CONF_CFG.manual;
        const sc = SEV_CFG[s.severity]    || SEV_CFG.warning;
        return (
          <div key={i} className="rounded-xl overflow-hidden animate-fade-in-up"
            style={{ animationDelay: `${i * .06}s`, background: '#1c2129', border: `1px solid ${sc.border}`, borderLeft: `3px solid ${sc.leftBar}` }}>
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#30363d' }}>
              <span className="font-mono font-bold text-sm text-white">{s.rule_id}</span>
              <span className="tag" style={{ background: cc.bg, color: cc.text, border: `1px solid ${cc.border}` }}>
                {cc.icon} {cc.label}
              </span>
            </div>

            <div className="p-4 space-y-3">
              {/* Explanation */}
              <div>
                <div className="text-[10px] uppercase tracking-[.08em] text-muted font-semibold mb-1.5">Why it failed</div>
                <p className="text-xs leading-relaxed" style={{ color: '#adbac7' }}>{s.explanation}</p>
              </div>

              {/* How to fix */}
              <div className="rounded-lg p-3" style={{ background: 'rgba(88,166,255,.05)', border: '1px solid rgba(88,166,255,.12)' }}>
                <div className="text-[10px] uppercase tracking-[.08em] text-accent font-semibold mb-1.5">How to fix</div>
                <p className="text-xs leading-relaxed text-text/80">{s.how_to_fix}</p>
              </div>

              {/* Field diff */}
              {s.field_corrections?.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-[.08em] text-muted font-semibold mb-2">Field corrections</div>
                  <div className="space-y-1.5">
                    {s.field_corrections.map((fc: any, j: number) => (
                      <div key={j} className="rounded-lg p-3" style={{ background: '#161b22', border: '1px solid #30363d' }}>
                        <div className="font-mono text-xs text-accent mb-2">{fc.field}</div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <div className="text-[9px] text-muted uppercase tracking-[.06em] mb-1">Current</div>
                            <code className="diff-old px-2 py-1 rounded text-[11px] block font-mono break-all">
                              {fc.current_value === null || fc.current_value === undefined ? 'null' : String(fc.current_value)}
                            </code>
                          </div>
                          <div>
                            <div className="text-[9px] text-muted uppercase tracking-[.06em] mb-1">Suggested</div>
                            {fc.suggested_value !== null && fc.suggested_value !== undefined
                              ? <code className="diff-new px-2 py-1 rounded text-[11px] block font-mono break-all">{String(fc.suggested_value)}</code>
                              : <span className="text-[11px] text-muted italic">requires manual input</span>}
                          </div>
                        </div>
                        {fc.note && <p className="text-[10px] text-muted mt-1.5 leading-relaxed">{fc.note}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Reference */}
              {s.reference && (
                <div className="border-t pt-2.5" style={{ borderColor: '#30363d' }}>
                  <div className="text-[10px] uppercase tracking-[.08em] text-muted font-semibold mb-1">Regulatory reference</div>
                  <p className="text-[11px] text-muted/70 italic leading-relaxed">{s.reference}</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ValidatePage() {
  const [examples,       setExamples]       = useState<any>({});
  const [domain,         setDomain]         = useState('healthcare');
  const [selectedLabel,  setSelectedLabel]  = useState('');
  const [json,           setJson]           = useState('');
  const [result,         setResult]         = useState<any>(null);
  const [suggestions,    setSuggestions]    = useState<any>(null);
  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [loading,        setLoading]        = useState(false);
  const [error,          setError]          = useState('');
  const [activeTab,      setActiveTab]      = useState<'result' | 'fix'>('result');

  useEffect(() => { api.examples().then(setExamples).catch(() => {}); }, []);

  const domExamples = (examples[domain === 'healthcare' ? 'healthcare' : 'finance']?.examples || []) as any[];

  const loadExample = (label: string) => {
    setSelectedLabel(label);
    const list = examples[domain === 'healthcare' ? 'healthcare' : 'finance']?.examples || [];
    const ex   = list.find((e: any) => `${e.category} — ${e.record_id}` === label);
    if (ex) setJson(JSON.stringify(ex.record, null, 2));
    setResult(null); setSuggestions(null);
  };

  const validate = async () => {
    setLoading(true); setResult(null); setSuggestions(null); setError(''); setActiveTab('result');
    try { setResult(await api.validate(domain, JSON.parse(json))); }
    catch (e: any) { setError(e.message || 'Validation failed'); }
    setLoading(false);
  };

  const fetchSuggestions = async () => {
    if (!result) return;
    setLoadingSuggest(true); setSuggestions(null);
    try {
      const res = await api.suggestFix(domain, JSON.parse(json), result.record_id);
      setSuggestions(res); setActiveTab('fix');
    } catch (e: any) { setError(e.message || 'Suggestion fetch failed'); }
    setLoadingSuggest(false);
  };

  const applyFix = () => {
    if (suggestions?.fixed_record) {
      setJson(JSON.stringify(suggestions.fixed_record, null, 2));
      setSuggestions(null); setResult(null); setActiveTab('result');
    }
  };

  const dc = result ? (DEC_CFG[result.decision] || DEC_CFG.quarantined) : null;
  const hasViolations = result?.violated_rules?.length > 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Validate Record</h1>
          <p className="text-sm text-muted mt-0.5">Full 4-stage pipeline · structural → semantic → confidence → routing</p>
        </div>
        {result && (
          <button onClick={() => downloadJSON(suggestions || result, `sg-${result.record_id}.json`)}
            className="text-xs text-muted hover:text-text border border-border hover:border-border-l rounded-lg px-3 py-2 transition flex items-center gap-1.5">
            ⬇ Export JSON
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-8">

        {/* ── LEFT — Input panel ── */}
        <div className="space-y-3">
          {/* Domain + example selectors */}
          <select value={domain}
            onChange={(e) => { setDomain(e.target.value); setSelectedLabel(''); setResult(null); setSuggestions(null); }}
            className="w-full rounded-lg px-3 py-2 text-sm text-text"
            style={{ background: '#1c2129', border: '1px solid #30363d' }}>
            <option value="healthcare">🏥 Healthcare Intake</option>
            <option value="finance">💰 Financial Loan Application</option>
          </select>

          {domExamples.length > 0 && (
            <select value={selectedLabel} onChange={(e) => loadExample(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm text-text"
              style={{ background: '#1c2129', border: '1px solid #30363d' }}>
              <option value="">— Load example record —</option>
              {domExamples.map((ex: any) => {
                const icon  = ex.category === 'valid' ? '✅' : ex.category === 'invalid' ? '❌' : '⚠️';
                const label = `${ex.category} — ${ex.record_id}`;
                return <option key={label} value={label}>{icon} {label}{ex.notes ? ` — ${ex.notes}` : ''}</option>;
              })}
            </select>
          )}

          {/* JSON editor */}
          <div className="relative">
            <textarea value={json} onChange={(e) => { setJson(e.target.value); setResult(null); setSuggestions(null); }}
              className="w-full rounded-xl p-4 text-text font-mono text-xs h-80 resize-none focus:outline-none transition"
              style={{ background: '#161b22', border: `1px solid ${json && !result ? '#3d444e' : '#30363d'}` }}
              placeholder='{ "patient_id": "P-1234", ... }' />
            {json && (
              <div className="absolute bottom-3 right-3 text-[10px] text-muted/50 font-mono">
                {json.split('\n').length} lines
              </div>
            )}
          </div>

          {/* Action buttons */}
          <button onClick={validate} disabled={loading || !json.trim()}
            className="w-full font-semibold py-3 rounded-xl transition text-white text-sm"
            style={{ background: loading ? '#1c2129' : '#1f6feb', border: '1px solid rgba(88,166,255,.3)',
                     opacity: !json.trim() ? .4 : 1 }}>
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Validating…
              </span>
            ) : '⬡  Validate Record'}
          </button>

          {result && hasViolations && (
            <button onClick={fetchSuggestions} disabled={loadingSuggest}
              className="w-full font-semibold py-2.5 rounded-xl transition text-sm"
              style={{ background: 'rgba(210,153,34,.1)', border: '1px solid rgba(210,153,34,.3)', color: '#e3b341',
                       opacity: loadingSuggest ? .5 : 1 }}>
              {loadingSuggest ? '⟳ Generating corrections…' : '🔧  Suggest Corrections'}
            </button>
          )}

          {suggestions?.total_fixable > 0 && (
            <button onClick={applyFix}
              className="w-full font-semibold py-2.5 rounded-xl transition text-sm"
              style={{ background: 'rgba(35,134,54,.12)', border: '1px solid rgba(35,134,54,.3)', color: '#3fb950' }}>
              ⚡ Apply Auto-Fixes ({suggestions.total_fixable} correction{suggestions.total_fixable !== 1 ? 's' : ''})
            </button>
          )}
        </div>

        {/* ── RIGHT — Results panel ── */}
        <div className="space-y-4">
          {error && (
            <div className="rounded-xl p-4 text-sm animate-fade-in"
              style={{ background: 'rgba(218,54,51,.08)', border: '1px solid rgba(218,54,51,.3)', color: '#f85149' }}>
              {error}
            </div>
          )}

          {!result && !error && (
            <div className="rounded-2xl p-16 text-center text-muted text-sm"
              style={{ background: '#161b22', border: '2px dashed #30363d' }}>
              <div className="text-2xl mb-3 opacity-30">⬡</div>
              Select an example or paste JSON, then click <strong className="text-accent">Validate Record</strong>
            </div>
          )}

          {result && dc && (
            <div className="space-y-4 animate-fade-in">

              {/* Decision card */}
              <div className="rounded-2xl p-6" style={{ background: dc.bg, border: `1px solid ${dc.border}`, boxShadow: dc.glow }}>
                <div className="flex items-center gap-6">
                  {/* Arc */}
                  <ConfidenceArc score={result.confidence_score || 0} decision={result.decision} />
                  {/* Right side */}
                  <div className="flex-1">
                    <div className="text-[10px] text-muted uppercase tracking-[.1em] font-semibold mb-1">Decision</div>
                    <div className="text-3xl font-black tracking-tight" style={{ color: dc.text }}>
                      {dc.icon} {dc.label}
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                      <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(0,0,0,.2)' }}>
                        <div className="text-muted text-[10px]">Structural</div>
                        <div className={`font-bold mt-0.5 ${result.structural_valid ? 'text-trusted' : 'text-quarantined'}`}>
                          {result.structural_valid ? '✓ PASS' : '✕ FAIL'}
                        </div>
                      </div>
                      <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(0,0,0,.2)' }}>
                        <div className="text-muted text-[10px]">Semantic</div>
                        <div className={`font-bold mt-0.5 ${result.semantic_valid ? 'text-trusted' : 'text-quarantined'}`}>
                          {result.semantic_valid ? '✓ PASS' : '✕ FAIL'}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Record ID + domain chip */}
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono text-muted">{result.record_id}</span>
                <span className="text-muted/40">·</span>
                <span className="tag" style={{ background: 'rgba(88,166,255,.1)', color: '#58a6ff', border: '1px solid rgba(88,166,255,.2)' }}>
                  {result.domain?.replace(/_/g,' ')}
                </span>
              </div>

              {/* Explanation */}
              {result.explanation && (
                <div className="rounded-xl p-4 text-sm leading-relaxed"
                  style={{ background: 'rgba(88,166,255,.05)', border: '1px solid rgba(88,166,255,.12)', color: '#adbac7' }}>
                  {result.explanation}
                </div>
              )}

              {/* Tab strip */}
              {suggestions && (
                <div className="flex rounded-xl overflow-hidden" style={{ background: '#1c2129', border: '1px solid #30363d' }}>
                  {(['result', 'fix'] as const).map(tab => (
                    <button key={tab} onClick={() => setActiveTab(tab)}
                      className="flex-1 py-2.5 text-xs font-semibold transition"
                      style={activeTab === tab
                        ? { background: 'rgba(88,166,255,.15)', color: '#58a6ff' }
                        : { color: '#8b949e' }}>
                      {tab === 'result' ? '⬡  Violations' : '🔧  Corrections'}
                    </button>
                  ))}
                </div>
              )}

              {/* Violations */}
              {(activeTab === 'result' || !suggestions) && hasViolations && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-white">
                      Violated Rules <span className="text-quarantined">{result.violated_rules.length}</span>
                    </h3>
                    <span className="text-[10px] text-muted">Click to expand · see why it matters</span>
                  </div>
                  <div className="stagger space-y-2">
                    {result.violated_rules.map((v: any, i: number) => (
                      <ViolationCard key={i} v={v} idx={i} />
                    ))}
                  </div>
                </div>
              )}

              {(activeTab === 'result' || !suggestions) && !hasViolations && result && (
                <div className="rounded-xl p-6 text-center" style={{ background: 'rgba(35,134,54,.06)', border: '1px solid rgba(35,134,54,.2)' }}>
                  <div className="text-2xl mb-2">✓</div>
                  <p className="text-sm text-trusted font-semibold">All rules passed</p>
                  <p className="text-xs text-muted mt-1">Record meets all structural and semantic requirements</p>
                </div>
              )}

              {/* Corrections panel */}
              {activeTab === 'fix' && suggestions && <SuggestionsPanel suggestions={suggestions} />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

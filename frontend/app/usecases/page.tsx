'use client';

const CASES = [
  {
    icon: '🏥',
    title: 'Healthcare Intake Validation',
    color: { bg:'rgba(35,134,54,.08)', border:'rgba(35,134,54,.2)', accent:'#3fb950' },
    problem: 'LLMs generating patient intake records produce temporal contradictions, age inconsistencies, and implausible diagnoses that pass schema checks but fail clinical logic.',
    rules: [
      { id:'HC-003', text:'Discharge before admission → quarantined' },
      { id:'HC-001', text:'Stated age vs computed DOB mismatch → flagged' },
      { id:'HC-004', text:'Adult-only ICD-10 code on paediatric patient → flagged' },
      { id:'HC-005', text:'Cardiac medication for UTI diagnosis → flagged' },
    ],
    outcome: 'Impossible records quarantined before entering EHR systems. Valid records flow through with full audit trail and confidence score.',
    stats: [{ label:'False quarantine rate', val:'0%' }, { label:'Semantic rules', val:'5' }, { label:'Avg latency', val:'0.09ms' }],
  },
  {
    icon: '💰',
    title: 'Loan Application Validation',
    color: { bg:'rgba(210,153,34,.08)', border:'rgba(210,153,34,.2)', accent:'#e3b341' },
    problem: 'LLM-generated loan applications contain extreme ratio violations, impossible employment histories, and temporal impossibilities that expose lenders to ATR compliance failures.',
    rules: [
      { id:'FN-002', text:'$2.5M loan on $48K income (52×) → quarantined' },
      { id:'FN-004', text:'18yr employment at age 24 → quarantined' },
      { id:'FN-001', text:'Approval date before application → quarantined' },
      { id:'FN-005', text:'Approved > requested amount → flagged' },
    ],
    outcome: 'Impossible applications quarantined. Edge cases flagged with confidence scores and specific rule violations for underwriter review.',
    stats: [{ label:'Rules covered', val:'5' }, { label:'Precision/Recall', val:'1.0 / 1.0' }, { label:'ATR violations caught', val:'100%' }],
  },
  {
    icon: '🏦',
    title: 'Insurance Claims Processing',
    color: { bg:'rgba(88,166,255,.08)', border:'rgba(88,166,255,.2)', accent:'#58a6ff' },
    problem: 'Automated claim generation produces impossible timelines — procedures billed before admission, medications for contradictory conditions, ages that change between fields.',
    rules: [
      { id:'HC-002', text:'Admission before date of birth → quarantined' },
      { id:'HC-003', text:'Negative LOS breaks DRG calculation → quarantined' },
      { id:'HC-005', text:'Medication-diagnosis mismatch → flagged' },
      { id:'HC-001', text:'Age inconsistency across fields → flagged' },
    ],
    outcome: 'Impossible claims blocked before reaching payers. Reduces denial rates, audit exposure, and HIPAA risk from corrupted records.',
    stats: [{ label:'Claim rejection rate', val:'↓ 0%' }, { label:'Audit trail', val:'Full JSONL' }, { label:'Domains', val:'HC + FN' }],
  },
  {
    icon: '🤖',
    title: 'LLM Output Governance',
    color: { bg:'rgba(218,54,51,.08)', border:'rgba(218,54,51,.2)', accent:'#f85149' },
    problem: 'Teams using GPT-4, Claude, or open-source models for structured generation rely on JSON Schema alone. Semantic quality degrades silently across model updates and prompt changes.',
    rules: [
      { id:'DRIFT', text:'Population-level shift detection via PSI + z-score' },
      { id:'RAG',   text:'Retrieved regulatory context in every explanation' },
      { id:'AUDIT', text:'Full JSONL audit trail for every validated record' },
      { id:'ROUTE', text:'Three-tier routing: trusted / flagged / quarantined' },
    ],
    outcome: 'Insert SchemaGuard between the LLM API and your database. Deterministic, auditable, explainable decisions for every record with zero false positives on valid data.',
    stats: [{ label:'Zero false quarantines', val:'✓' }, { label:'Records/second', val:'~3,800' }, { label:'p99 latency', val:'3ms' }],
  },
];


export default function UseCasesPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Use Cases</h1>
        <p className="text-sm text-muted mt-0.5">
          Real-world scenarios where SchemaGuard prevents LLM data-quality failures
        </p>
      </div>

      {/* Case grid */}
      <div className="grid grid-cols-2 gap-5 stagger">
        {CASES.map((c, i) => (
          <div key={i}
            className="card-hover animate-fade-in-up rounded-2xl overflow-hidden flex flex-col"
            style={{ background:'#161b22', border:`1px solid ${c.color.border}` }}>

            {/* Card header */}
            <div style={{ background:`linear-gradient(135deg,${c.color.bg} 0%,rgba(22,27,34,.6) 100%)`,
                          borderBottom:`1px solid ${c.color.border}`, padding:'20px 24px' }}>
              <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:10 }}>
                <span style={{ fontSize:22 }}>{c.icon}</span>
                <h2 style={{ fontSize:16, fontWeight:700, color:'#fff', letterSpacing:'-.01em' }}>
                  {c.title}
                </h2>
              </div>
              <p style={{ fontSize:12, color:'rgba(173,186,199,.75)', lineHeight:1.6 }}>
                {c.problem}
              </p>
            </div>

            <div style={{ padding:'16px 24px', flex:1, display:'flex', flexDirection:'column', gap:14 }}>
              {/* Rules caught */}
              <div>
                <div style={{ fontSize:10, color:'#8b949e', textTransform:'uppercase',
                               letterSpacing:'.08em', fontWeight:600, marginBottom:8 }}>
                  Rules applied
                </div>
                <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
                  {c.rules.map((r, j) => (
                    <div key={j} style={{ display:'flex', alignItems:'flex-start', gap:8, fontSize:12 }}>
                      <span style={{ padding:'1px 6px', borderRadius:12, fontSize:9, fontWeight:700,
                                     background:`${c.color.bg}`, color:c.color.accent,
                                     border:`1px solid ${c.color.border}`, flexShrink:0, marginTop:1,
                                     fontFamily:'monospace', letterSpacing:'.02em' }}>
                        {r.id}
                      </span>
                      <span style={{ color:'rgba(173,186,199,.8)', lineHeight:1.4 }}>{r.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Outcome */}
              <div style={{ background:`${c.color.bg}`, border:`1px solid ${c.color.border}`,
                             borderRadius:10, padding:'12px 14px', marginTop:'auto' }}>
                <div style={{ fontSize:10, color:c.color.accent, textTransform:'uppercase',
                               letterSpacing:'.08em', fontWeight:600, marginBottom:4 }}>
                  ✓ Outcome
                </div>
                <p style={{ fontSize:12, color:'rgba(173,186,199,.85)', lineHeight:1.55 }}>
                  {c.outcome}
                </p>
              </div>

              {/* Stats row */}
              <div style={{ display:'flex', gap:0, borderTop:'1px solid #21262d', paddingTop:12 }}>
                {c.stats.map((st, k) => (
                  <div key={k} style={{ flex:1, textAlign:'center',
                                         borderRight: k<c.stats.length-1 ? '1px solid #21262d' : 'none' }}>
                    <div style={{ fontSize:13, fontWeight:700, color:c.color.accent,
                                   fontVariantNumeric:'tabular-nums' }}>{st.val}</div>
                    <div style={{ fontSize:10, color:'#8b949e', marginTop:2 }}>{st.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Integration pattern */}
      <div style={{ background:'#161b22', border:'1px solid #30363d', borderRadius:16, padding:24 }}>
        <h2 className="text-base font-semibold text-white mb-4">Integration Pattern</h2>
        <div style={{ display:'flex', alignItems:'center', gap:0, overflowX:'auto' }}>
          {[
            { label:'LLM API', sub:'GPT-4 · Claude · Llama', bg:'#1c2129', border:'#30363d', text:'#8b949e' },
            null,
            { label:'SchemaGuard', sub:'4-stage validation pipeline', bg:'rgba(88,166,255,.1)', border:'rgba(88,166,255,.3)', text:'#58a6ff' },
            null,
            { label:'Trusted', sub:'Auto-insert → DB', bg:'rgba(35,134,54,.1)', border:'rgba(35,134,54,.3)', text:'#3fb950' },
            { label:'Flagged', sub:'Review queue', bg:'rgba(210,153,34,.1)', border:'rgba(210,153,34,.3)', text:'#e3b341' },
            { label:'Quarantined', sub:'Reject + alert', bg:'rgba(218,54,51,.1)', border:'rgba(218,54,51,.3)', text:'#f85149' },
          ].map((node, i) =>
            node === null ? (
              <div key={i} style={{ fontSize:16, color:'#30363d', padding:'0 8px', flexShrink:0 }}>→</div>
            ) : (
              <div key={i} style={{ background:node.bg, border:`1px solid ${node.border}`,
                                     borderRadius:10, padding:'10px 14px', textAlign:'center',
                                     minWidth:110, flexShrink:0 }}>
                <div style={{ fontSize:12, fontWeight:700, color:node.text }}>{node.label}</div>
                <div style={{ fontSize:10, color:'#8b949e', marginTop:2 }}>{node.sub}</div>
              </div>
            )
          )}
        </div>
        <p className="text-xs text-muted mt-4 leading-relaxed">
          Drop SchemaGuard between your LLM and your database. Every record gets a deterministic decision —
          no hallucinated pass/fail, no silent quality drift. Full audit trail in JSONL, drift alerts via PSI
          and z-score, RAG-augmented explanations for flagged records.
        </p>
      </div>
    </div>
  );
}

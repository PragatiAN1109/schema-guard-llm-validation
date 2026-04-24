'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

const RULE_DOCS: Record<string, { why: string; ref: string; example: string }> = {
  'HC-001': {
    why:     'Age discrepancies cause wrong dosage protocols, incorrect paediatric/adult classification, and billing rejections under CMS age-edit checks.',
    ref:     'HL7 FHIR R4 §Patient.birthDate · CMS CoP §482.24(c)',
    example: 'Stated age 52, but date_of_birth + admission_date compute age 34 → 18-year gap is implausible.',
  },
  'HC-002': {
    why:     'Admission before birth is physically impossible. Indicates corrupted DOB or wrong year in the admission date — both prevent correct claim adjudication.',
    ref:     'HL7 FHIR R4 §Patient.birthDate · Joint Commission RC.02.01.01',
    example: 'date_of_birth: 2025-03-15, admission_date: 2024-09-14 → patient not yet born.',
  },
  'HC-003': {
    why:     'Negative length-of-stay breaks DRG calculation, causes UB-04 claim rejection, and corrupts LOS quality metrics.',
    ref:     'NUBC UB-04 FL6/FL16 · CMS ICD-10-PCS §482.24(c)(2)(vii)',
    example: 'admission_date: 2024-08-15, discharge_date: 2024-08-08 → LOS = −7 days.',
  },
  'HC-004': {
    why:     'Age-restricted ICD-10 codes assigned to wrong age groups cause claim denials, quality-measure errors, and NCCI edit failures.',
    ref:     'ICD-10-CM Official Guidelines §I.C Age/Sex Edits · CMS NCCI',
    example: 'M81.0 (age-related osteoporosis) on a 5-year-old → adult-only code.',
  },
  'HC-005': {
    why:     'Medication-diagnosis mismatches indicate copy-paste errors or formulary confusion, creating potential patient safety events and pharmacy review flags.',
    ref:     'ISMP Medication Safety Alert · Joint Commission NPSG.03.04.01',
    example: 'Diagnosis N39.0 (UTI) but medication Metoprolol (cardiac) → no clinical rationale.',
  },
  'FN-001': {
    why:     'Temporal impossibility violates TILA-RESPA disclosure timelines and makes the loan ineligible for QM safe-harbour protection.',
    ref:     'CFPB TRID §1026.19 · Regulation B §1002.9',
    example: 'application_date: 2024-07-20, approval_date: 2024-06-28 → approved 22 days before applying.',
  },
  'FN-002': {
    why:     'Loan-to-income above 10× violates CFPB Ability-to-Repay rules. The loan is ineligible for GSE purchase and QM protection.',
    ref:     'CFPB Regulation Z §1026.43(c) · Fannie Mae Selling Guide B3-6-02',
    example: '$2.5M loan on $48K income = 52× LTI (limit: 10×).',
  },
  'FN-003': {
    why:     'High DTI is the leading predictor of default. Fannie Mae DU rejects back-end DTI above limits and requires manual underwriter review.',
    ref:     'CFPB QM Standard — 43% safe harbour · Fannie Mae DU §B3-6-02',
    example: '$50K debt on $60K income = 83% DTI (limit: 60% warning threshold).',
  },
  'FN-004': {
    why:     'Employment longer than the applicant has been alive flags identity fraud or data entry error. ATR income verification fails.',
    ref:     'FLSA Child Labour §29 CFR Part 570 · CFPB ATR §1026.43(c)(3)',
    example: '24-year-old claiming 18 years employment → would have started at age 6.',
  },
  'FN-005': {
    why:     'Approving above requested requires a RESPA counter-offer disclosure. Silent over-approval is an ECOA violation.',
    ref:     'CFPB Regulation B (ECOA) §1002.9 · RESPA §12 CFR Part 1024',
    example: '$400K approved against $320K requested → $80K excess requires counter-offer notice.',
  },
};

const DOMAIN_LABELS: Record<string, string> = {
  healthcare_intake:           '🏥 Healthcare Intake',
  financial_loan_application:  '💰 Financial Loan Application',
};

export default function RulesPage() {
  const [data, setData]       = useState<any>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => { api.rules().then(setData).catch(() => {}); }, []);

  const domains = data?.domains || {};

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Rules Library</h1>
        <p className="text-sm text-muted mt-0.5">
          {data?.total_rules || 10} semantic validation rules · click any rule to see why it matters
        </p>
      </div>

      {Object.entries(domains).map(([domain, rules]: [string, any]) => (
        <div key={domain} className="space-y-2">
          <h2 className="text-base font-semibold text-white">{DOMAIN_LABELS[domain] || domain}</h2>
          <div className="space-y-2">
            {(rules as any[]).map((r: any, i: number) => {
              const doc  = RULE_DOCS[r.rule_id];
              const open = expanded === r.rule_id;
              const isCrit = r.severity === 'critical';
              return (
                <div key={r.rule_id}
                  className="rounded-xl overflow-hidden animate-fade-in-up"
                  style={{ animationDelay: `${i * .05}s`, background: '#161b22',
                    border: `1px solid ${open ? (isCrit ? 'rgba(218,54,51,.4)' : 'rgba(210,153,34,.4)') : '#30363d'}`,
                    borderLeft: `3px solid ${isCrit ? '#da3633' : '#d29922'}` }}>

                  {/* Rule header row — clickable */}
                  <button className="w-full text-left flex items-start gap-4 px-5 py-4"
                    onClick={() => setExpanded(open ? null : r.rule_id)}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-mono font-bold text-sm text-white">{r.rule_id}</span>
                        <span className="text-[10px] font-mono text-muted">{r.rule_name}</span>
                        <span className="tag"
                          style={{ background: isCrit ? 'rgba(218,54,51,.12)' : 'rgba(210,153,34,.12)',
                                   color: isCrit ? '#f85149' : '#e3b341',
                                   border: `1px solid ${isCrit ? 'rgba(218,54,51,.3)' : 'rgba(210,153,34,.3)'}` }}>
                          {r.severity}
                        </span>
                      </div>
                      <div className="text-xs text-muted mt-1">
                        Fields: <span className="font-mono text-text/70">{r.fields?.join(', ')}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">
                      <span className="text-[11px] text-accent">{open ? 'Hide' : 'Why it matters'}</span>
                      <span className="text-muted text-xs">{open ? '▲' : '▼'}</span>
                    </div>
                  </button>

                  {/* Expanded details */}
                  {open && doc && (
                    <div className="px-5 pb-5 pt-0 space-y-3 border-t animate-fade-in"
                      style={{ borderColor: '#21262d' }}>
                      <div className="mt-3 rounded-lg p-4"
                        style={{ background: 'rgba(88,166,255,.05)', border: '1px solid rgba(88,166,255,.12)' }}>
                        <div className="text-[10px] font-semibold text-accent uppercase tracking-[.08em] mb-1.5 flex items-center gap-1.5">
                          ⚡ Why This Matters
                        </div>
                        <p className="text-xs text-text/80 leading-relaxed">{doc.why}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-lg p-3" style={{ background: '#1c2129', border: '1px solid #30363d' }}>
                          <div className="text-[10px] font-semibold text-muted uppercase tracking-[.08em] mb-1.5">
                            Example violation
                          </div>
                          <p className="text-xs text-text/70 leading-relaxed font-mono">{doc.example}</p>
                        </div>
                        <div className="rounded-lg p-3" style={{ background: '#1c2129', border: '1px solid #30363d' }}>
                          <div className="text-[10px] font-semibold text-muted uppercase tracking-[.08em] mb-1.5">
                            Regulatory reference
                          </div>
                          <p className="text-[11px] text-muted/80 italic leading-relaxed">{doc.ref}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {!data && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
        </div>
      )}
    </div>
  );
}

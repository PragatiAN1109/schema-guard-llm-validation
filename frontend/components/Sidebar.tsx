'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/',          label: 'Dashboard',    icon: '◈',  desc: 'Overview & metrics' },
  { href: '/validate',  label: 'Validate',      icon: '⬡',  desc: 'Single record' },
  { href: '/batch',     label: 'Batch',          icon: '⬡⬡', desc: 'Bulk processing' },
  { href: '/rules',     label: 'Rules Library', icon: '▦',  desc: '10 semantic rules' },
  { href: '/audit',     label: 'Audit Trail',   icon: '≡',  desc: 'Full history' },
  { href: '/usecases',  label: 'Use Cases',     icon: '◎',  desc: 'Industry examples' },
];

const SERVICES = [
  { label: 'Validation Engine',  color: '#238636' },
  { label: 'Scoring Pipeline',   color: '#238636' },
  { label: 'Drift Detection',    color: '#238636' },
  { label: 'Async Queue',        color: '#238636' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-surface border-r border-border flex flex-col z-50"
      style={{ background: 'linear-gradient(180deg, #1c2129 0%, #161b22 100%)' }}>

      {/* Logo */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base font-bold"
            style={{ background: 'rgba(88,166,255,.15)', border: '1px solid rgba(88,166,255,.25)', color: '#58a6ff' }}>
            SG
          </div>
          <div>
            <div className="text-[15px] font-extrabold text-white tracking-tight">SchemaGuard</div>
            <div className="text-[9px] text-muted tracking-[.12em] uppercase mt-px">Validation Console</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all group ${
                active
                  ? 'text-accent font-semibold'
                  : 'text-muted hover:text-text'
              }`}
              style={active ? { background: 'rgba(88,166,255,.1)', border: '1px solid rgba(88,166,255,.18)' } : { border: '1px solid transparent' }}
            >
              <span className={`text-[15px] w-5 text-center opacity-80 ${active ? 'opacity-100' : 'group-hover:opacity-100'}`}
                style={{ fontFamily: 'monospace' }}>
                {item.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className={active ? 'text-accent' : ''}>{item.label}</div>
                <div className="text-[10px] text-muted/60 mt-px hidden group-hover:block">{item.desc}</div>
              </div>
              {active && <span className="w-1.5 h-1.5 rounded-full bg-accent" />}
            </Link>
          );
        })}
      </nav>

      {/* Services status */}
      <div className="p-4 border-t border-border space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-[.1em] font-medium mb-2">System Status</div>
        {SERVICES.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-[11px] text-muted">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse-slow" style={{ background: s.color }} />
            {s.label}
          </div>
        ))}
        <div className="text-[10px] text-muted/40 mt-3 pt-2 border-t border-border/50">
          v0.3.0 · 2 domains · 10 rules
        </div>
      </div>
    </aside>
  );
}

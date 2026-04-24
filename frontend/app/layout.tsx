import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata = {
  title: 'SchemaGuard Console',
  description: 'Validation and Governance for LLM Structured Outputs',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="flex min-h-screen bg-bg">
        <Sidebar />
        <div className="flex-1 ml-64 flex flex-col">
          <header className="sticky top-0 z-40 h-14 bg-surface/80 backdrop-blur-md border-b border-border flex items-center px-8">
            <div className="text-xs text-muted font-medium tracking-wide">SchemaGuard Console</div>
            <div className="flex-1" />
            <div className="flex items-center gap-4 text-xs text-muted">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-trusted animate-pulse" />
                All Systems Operational
              </span>
            </div>
          </header>
          <main className="flex-1 p-8 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}

import type { Metadata } from 'next';
import { Syne, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const syne = Syne({
  subsets: ['latin'],
  variable: '--font-syne',
  weight: ['400', '500', '600', '700', '800'],
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500'],
});

export const metadata: Metadata = {
  title: 'Agent Forge — Multi-Agent Orchestration',
  description: 'Orchestrate AI agents to research, write, and review complex reports.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${syne.variable} ${mono.variable}`}>
      <body>
        <nav style={{
          borderBottom: '1px solid rgba(99,179,237,0.08)',
          backdropFilter: 'blur(12px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          background: 'rgba(7,11,18,0.85)',
        }}>
          <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
            <a href="/" className="nav-logo">
              <div className="nav-logo-mark">A</div>
              <span className="nav-logo-text">
                Agent<span className="nav-logo-accent">Forge</span>
              </span>
            </a>
            <a href="/tasks" className="nav-link">
              Task History →
            </a>
          </div>
        </nav>

        <main className="max-w-6xl mx-auto px-6 py-10">
          {children}
        </main>
      </body>
    </html>
  );
}
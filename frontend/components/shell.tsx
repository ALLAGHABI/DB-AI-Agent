'use client';
import { Database } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { LangThemeToggles } from './lang-theme-toggles';

export function Shell({ sidebar, main, connected }: {
  sidebar: React.ReactNode; main: React.ReactNode; connected: boolean;
}) {
  const t = useTranslations('app');
  const ts = useTranslations('status');
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-2.5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-bold leading-tight">{t('name')}</div>
              <div className="text-xs text-muted-foreground leading-tight">{t('tagline')}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={connected ? 'default' : 'secondary'} className="gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-primary-foreground' : 'bg-muted-foreground'}`} />
              {connected ? ts('connected') : ts('disconnected')}
            </Badge>
            <LangThemeToggles />
          </div>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl gap-4 p-4 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4">{sidebar}</aside>
        <main className="min-w-0 space-y-4">{main}</main>
      </div>
    </div>
  );
}

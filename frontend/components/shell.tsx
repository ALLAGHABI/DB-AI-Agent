'use client';
import { Database, Mail, Phone } from 'lucide-react';

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56v-1.97c-3.2.7-3.87-1.54-3.87-1.54-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.75 2.69 1.25 3.34.95.1-.74.4-1.25.73-1.54-2.55-.29-5.23-1.28-5.23-5.68 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.58.23 2.75.11 3.04.74.81 1.18 1.83 1.18 3.09 0 4.41-2.69 5.38-5.25 5.67.41.35.78 1.05.78 2.13v3.16c0 .31.21.68.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

function LinkedinIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05a3.74 3.74 0 0 1 3.37-1.85c3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  );
}
import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { LangThemeToggles } from './lang-theme-toggles';

const AUTHOR = {
  name: 'ALI ALLAGHABI',
  phone: '+966551499154',
  email: 'ALI.ALLAGHABI@gmail.com',
  github: 'https://github.com/ALLAGHABI',
  linkedin: 'https://www.linkedin.com/in/aliallaghabi/',
};

export function Shell({ sidebar, main, connected, apiDown = false, modeSwitch, showStatus = true }: {
  sidebar: React.ReactNode; main: React.ReactNode; connected: boolean;
  apiDown?: boolean; modeSwitch?: React.ReactNode; showStatus?: boolean;
}) {
  const t = useTranslations('app');
  const ts = useTranslations('status');
  return (
    <div className="min-h-screen bg-background text-foreground">
      <a href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground">
        {t('skipToContent')}
      </a>
      <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex min-h-14 max-w-7xl flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h1 className="truncate text-sm font-bold leading-tight">{t('name')}</h1>
              <p className="truncate text-xs text-muted-foreground leading-tight">{t('tagline')}</p>
            </div>
          </div>
          {modeSwitch}
          <div className="flex items-center gap-3">
            {showStatus && (
              <Badge variant={connected ? 'default' : 'secondary'} className="gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-primary-foreground' : 'bg-muted-foreground'}`} />
                {connected ? ts('connected') : ts('disconnected')}
              </Badge>
            )}
            <LangThemeToggles />
          </div>
        </div>
      </header>
      {apiDown && (
        <div role="alert" className="border-b border-destructive/40 bg-destructive/10 px-4 py-2 text-center text-xs text-destructive">
          {t('apiDown')}
        </div>
      )}
      <div className="mx-auto grid max-w-7xl gap-4 p-4 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4" aria-label={t('settingsRegion')}>{sidebar}</aside>
        <main id="main" className="min-w-0 space-y-4">{main}</main>
      </div>
      <footer className="border-t">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-3 text-xs text-muted-foreground">
          <span className="font-medium">{t('builtBy')} {AUTHOR.name}</span>
          <div className="flex flex-wrap items-center gap-4" dir="ltr">
            <a className="flex items-center gap-1.5 hover:text-foreground" href={`tel:${AUTHOR.phone}`}>
              <Phone className="h-3.5 w-3.5" />{AUTHOR.phone}
            </a>
            <a className="flex items-center gap-1.5 hover:text-foreground" href={`mailto:${AUTHOR.email}`}>
              <Mail className="h-3.5 w-3.5" />{AUTHOR.email}
            </a>
            <a className="flex items-center gap-1.5 hover:text-foreground" href={AUTHOR.github} target="_blank" rel="noreferrer">
              <GithubIcon className="h-3.5 w-3.5" />GitHub
            </a>
            <a className="flex items-center gap-1.5 hover:text-foreground" href={AUTHOR.linkedin} target="_blank" rel="noreferrer">
              <LinkedinIcon className="h-3.5 w-3.5" />LinkedIn
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

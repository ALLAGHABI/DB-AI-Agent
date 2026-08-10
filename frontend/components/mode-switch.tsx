'use client';
import { Database, FileBarChart } from 'lucide-react';
import { useTranslations } from 'next-intl';

export type AppMode = 'database' | 'reports';

const MODES: { id: AppMode; Icon: typeof Database }[] = [
  { id: 'database', Icon: Database },
  { id: 'reports', Icon: FileBarChart },
];

/** مبدّل الوضع — أداتان في منتج واحد، بنقرة واحدة وبلا فقدان حالة. */
export function ModeSwitch({ mode, onChange }: {
  mode: AppMode; onChange: (m: AppMode) => void;
}) {
  const t = useTranslations('modes');

  return (
    <div role="group" aria-label={t('label')}
      className="flex items-center gap-0.5 rounded-xl bg-muted p-0.5">
      {MODES.map(({ id, Icon }) => {
        const active = mode === id;
        return (
          <button key={id} type="button" aria-pressed={active}
            onClick={() => onChange(id)}
            className={`flex cursor-pointer items-center gap-1.5 rounded-[10px] px-3 py-1.5 text-xs font-medium transition-colors
              ${active
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'}`}>
            <Icon className={`h-3.5 w-3.5 ${active ? 'text-primary' : ''}`} aria-hidden />
            <span className="hidden sm:inline">{t(id)}</span>
          </button>
        );
      })}
    </div>
  );
}

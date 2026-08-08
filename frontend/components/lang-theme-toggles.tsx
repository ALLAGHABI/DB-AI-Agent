'use client';
import { Languages, Moon, Sun } from 'lucide-react';
import { useLocale } from 'next-intl';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';

export function LangThemeToggles() {
  const { theme, setTheme } = useTheme();
  const locale = useLocale();

  const switchLocale = () => {
    document.cookie = `locale=${locale === 'ar' ? 'en' : 'ar'};path=/;max-age=31536000`;
    location.reload();
  };

  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="sm" onClick={switchLocale} className="gap-1.5">
        <Languages className="h-4 w-4" />
        <span className="text-xs font-medium">{locale === 'ar' ? 'EN' : 'ع'}</span>
      </Button>
      <Button variant="ghost" size="icon" aria-label="theme"
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
        <Sun className="h-4 w-4 dark:hidden" />
        <Moon className="hidden h-4 w-4 dark:block" />
      </Button>
    </div>
  );
}

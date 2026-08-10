'use client';
import { Languages, Moon, Sun } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';

export function LangThemeToggles() {
  const { theme, setTheme } = useTheme();
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations('app');
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isDark = mounted ? theme === 'dark' : undefined;

  // تبديل اللغة بلا إعادة تحميل — الحالة (نص الاستعلام، النتائج) تبقى كما هي
  const switchLocale = () => {
    document.cookie = `locale=${locale === 'ar' ? 'en' : 'ar'};path=/;max-age=31536000`;
    router.refresh();
  };

  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="sm" onClick={switchLocale} className="gap-1.5"
        aria-label={t('switchLanguage')}>
        <Languages className="h-4 w-4" aria-hidden />
        <span className="text-xs font-medium" lang={locale === 'ar' ? 'en' : 'ar'}>
          {locale === 'ar' ? 'EN' : 'ع'}
        </span>
      </Button>
      <Button variant="ghost" size="icon" aria-pressed={isDark}
        aria-label={t(isDark ? 'switchToLight' : 'switchToDark')}
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
        <Sun className="h-4 w-4 dark:hidden" />
        <Moon className="hidden h-4 w-4 dark:block" />
      </Button>
    </div>
  );
}

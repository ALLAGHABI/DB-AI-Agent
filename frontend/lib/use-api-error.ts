'use client';
import { useMessages, useTranslations } from 'next-intl';
import { useCallback } from 'react';
import { toast } from 'sonner';
import { ApiError } from './api';

/** يحوّل رمز الخطأ القادم من الباكند إلى رسالة بلغة المستخدم. */
export function useApiError() {
  const t = useTranslations('errors');
  const messages = useMessages() as { errors?: Record<string, string> } | undefined;

  const format = useCallback((e: unknown): string => {
    const known = (code: string) => Boolean(messages?.errors?.[code]);
    try {
      if (e instanceof ApiError) {
        const key = known(e.code) ? e.code : 'generic';
        return t(key, { detail: '', ...e.params } as never);
      }
      return t('generic', { detail: (e as Error)?.message ?? '' } as never);
    } catch {
      // آخر خط دفاع — لا يجوز أن يفشل عرض الخطأ نفسه
      return (e as Error)?.message ?? 'Error';
    }
  }, [t, messages]);

  const showError = useCallback((e: unknown) => {
    toast.error(format(e));
  }, [format]);

  return { format, showError };
}

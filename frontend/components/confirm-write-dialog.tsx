'use client';
import { AlertTriangle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';

export function ConfirmWriteDialog({ sql, onConfirm, onCancel }: {
  sql: string | null; onConfirm: () => void; onCancel: () => void;
}) {
  const t = useTranslations('query');
  return (
    <Dialog open={!!sql} onOpenChange={open => !open && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />{t('confirmTitle')}
          </DialogTitle>
          <DialogDescription>{t('confirmBody')}</DialogDescription>
        </DialogHeader>
        <pre dir="ltr" className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-sm">
          {sql}
        </pre>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onCancel}>{t('cancel')}</Button>
          <Button variant="destructive" onClick={onConfirm}>{t('confirmRun')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

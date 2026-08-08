import type { Metadata } from 'next';
import { IBM_Plex_Sans_Arabic, Inter } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import { ThemeProvider } from 'next-themes';
import { Toaster } from '@/components/ui/sonner';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const plexArabic = IBM_Plex_Sans_Arabic({
  subsets: ['arabic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-arabic',
});

export const metadata: Metadata = {
  title: 'SmartDB — AI Database Manager',
  description: 'Local-first AI database management & reporting',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  const dir = locale === 'ar' ? 'rtl' : 'ltr';
  return (
    <html lang={locale} dir={dir} suppressHydrationWarning
      className={`${inter.variable} ${plexArabic.variable}`}
      style={{ fontFamily: dir === 'rtl'
        ? 'var(--font-arabic), var(--font-inter), sans-serif'
        : 'var(--font-inter), var(--font-arabic), sans-serif' }}>
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <NextIntlClientProvider messages={messages}>
            {children}
            <Toaster richColors position={dir === 'rtl' ? 'bottom-left' : 'bottom-right'} />
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

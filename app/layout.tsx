import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '智药问点 — 药品说明书问答系统',
  description: '快速查找药品说明书中的相关信息。',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

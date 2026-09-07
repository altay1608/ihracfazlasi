import type { Metadata } from 'next';
import AdminLayoutShell from './AdminLayoutShell';

export const metadata: Metadata = {
  title: 'Admin Paneli | İhraç Fazlası Giyim',
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminLayoutShell>{children}</AdminLayoutShell>;
}

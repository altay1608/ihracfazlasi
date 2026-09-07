'use client';

import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';

const navGroups = [
  {
    label: 'Genel',
    items: [{ href: '/admin', label: 'Genel Bakış', icon: '⌂', exact: true }],
  },
  {
    label: 'Web Sitesi Yönetimi',
    items: [
      { href: '/admin/urunler', label: 'Ürünler', icon: '◇' },
      { href: '/admin/satislar', label: 'Satışlar', icon: '◉' },
      { href: '/admin/raporlar', label: 'Raporlar', icon: '▤' },
    ],
  },
  {
    label: 'Ayarlar',
    items: [{ href: '/admin/kategoriler', label: 'Kategoriler', icon: '◫' }],
  },
];

export default function AdminLayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const managementPanelUrl = process.env.NEXT_PUBLIC_MANAGEMENT_PANEL_URL || '/panel';

  const isLoginPage = pathname === '/admin/login';

  if (isLoginPage) {
    return (
      <div className="fixed inset-0 z-[100] bg-gray-50 flex items-center justify-center">
        {children}
      </div>
    );
  }

  const handleLogout = async () => {
    await fetch('/api/admin/auth', { method: 'DELETE' });
    router.push('/admin/login');
  };

  return (
    <div className="fixed inset-0 z-[100] bg-[#f4f5f7] flex overflow-hidden">
      {menuOpen && (
        <button
          aria-label="Menüyü kapat"
          className="fixed inset-0 z-30 bg-black/45 lg:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-72 bg-[#111827] text-white flex flex-col shrink-0 transition-transform lg:static lg:translate-x-0 ${menuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-5 border-b border-white/10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-400 text-gray-950 flex items-center justify-center font-black">İF</div>
          <div>
            <h1 className="text-sm font-bold text-white">İhraç Fazlası Giyim</h1>
            <p className="text-xs text-gray-400 mt-0.5">Mağaza Yönetimi</p>
          </div>
        </div>

        <nav className="flex-1 p-3 overflow-y-auto space-y-5">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="px-3 mb-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-[0.16em]">{group.label}</p>
              <ul className="space-y-1">
                {group.items.map((item) => {
                  const isActive = 'exact' in item && item.exact
                    ? pathname === item.href
                    : pathname.startsWith(item.href);
                  return (
                    <li key={item.href}>
                      <Link href={item.href} onClick={() => setMenuOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${isActive ? 'bg-amber-400 text-gray-950 font-semibold' : 'text-gray-300 hover:bg-white/10 hover:text-white'}`}>
                        <span className="w-5 text-center text-base">{item.icon}</span>
                        <span>{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          <div className="pt-4 border-t border-white/10">
            <p className="px-3 mb-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-[0.16em]">Ayrı Yönetim Sistemi</p>
            <Link
              href={managementPanelUrl}
              target={managementPanelUrl.startsWith('http') ? '_blank' : undefined}
              className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm bg-white/5 border border-white/10 text-amber-300 hover:bg-white/10 hover:text-amber-200 transition-colors"
            >
              <span className="w-5 text-center text-base">⊞</span>
              <span className="flex-1">Yeni Mağaza Paneli</span>
              <span aria-hidden="true">↗</span>
            </Link>
            <p className="px-3 mt-2 text-[11px] leading-relaxed text-gray-500">Stok, kasa, finans, personel ve gelişmiş raporlar</p>
          </div>
        </nav>

        <div className="p-3 border-t border-gray-700">
          <Link href="/" target="_blank" className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-gray-200 transition-colors mb-1">
            <span>↗</span>
            <span>Siteyi Görüntüle</span>
          </Link>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-red-400 hover:bg-gray-700 hover:text-red-300 transition-colors"
          >
            <span>←</span>
            <span>Çıkış Yap</span>
          </button>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto bg-[#f4f5f7] min-w-0">
        <div className="lg:hidden sticky top-0 z-20 h-16 bg-white/95 backdrop-blur border-b border-gray-200 flex items-center justify-between px-4">
          <button onClick={() => setMenuOpen(true)} className="w-10 h-10 rounded-lg border border-gray-200 text-xl">☰</button>
          <p className="font-semibold text-gray-900">Mağaza Yönetimi</p>
          <Link href="/" className="text-sm text-gray-500">Site ↗</Link>
        </div>
        <div className="max-w-[1600px] mx-auto">{children}</div>
      </main>
    </div>
  );
}

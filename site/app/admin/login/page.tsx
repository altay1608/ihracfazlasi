'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/admin/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        router.push('/admin');
        router.refresh();
      } else {
        const data = await res.json();
        setError(data.message || 'Yanlış şifre');
      }
    } catch {
      setError('Bağlantı hatası');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#0b1220] grid lg:grid-cols-[1.1fr_.9fr]">
      <section className="hidden lg:flex relative overflow-hidden p-12 flex-col justify-between text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(251,191,36,.2),transparent_35%),radial-gradient(circle_at_80%_80%,rgba(59,130,246,.16),transparent_35%)]" />
        <div className="relative flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-amber-400 text-gray-950 flex items-center justify-center font-black text-lg">İF</div>
          <div>
            <p className="font-bold text-lg">İhraç Fazlası Giyim</p>
            <p className="text-sm text-slate-400">Dijital Mağaza Merkezi</p>
          </div>
        </div>
        <div className="relative max-w-xl">
          <span className="inline-flex px-3 py-1 rounded-full bg-white/10 border border-white/10 text-xs text-amber-300 mb-5">TEK PANEL · TÜM OPERASYON</span>
          <h1 className="text-5xl font-bold leading-tight tracking-tight">Mağazanızın tüm kontrolü tek ekranda.</h1>
          <p className="mt-5 text-lg text-slate-300 leading-relaxed">Ürün, stok, satış, kasa, finans ve raporlar güvenli yönetim panelinizde birlikte çalışır.</p>
          <div className="grid grid-cols-3 gap-3 mt-8">
            {['Canlı stok', 'Finans takibi', 'Satış raporu'].map((item) => <div key={item} className="rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-slate-200">✓ {item}</div>)}
          </div>
        </div>
        <p className="relative text-xs text-slate-500">Yetkili personel erişimi · Güvenli oturum</p>
      </section>

      <section className="bg-[#f8fafc] flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 justify-center mb-8">
            <div className="w-11 h-11 rounded-xl bg-amber-400 text-gray-950 flex items-center justify-center font-black">İF</div>
            <div><p className="font-bold text-gray-900">İhraç Fazlası Giyim</p><p className="text-xs text-gray-500">Mağaza Yönetimi</p></div>
          </div>
          <div className="bg-white rounded-3xl border border-slate-200 shadow-[0_24px_80px_rgba(15,23,42,.12)] p-7 sm:p-9">
            <div className="mb-8">
              <p className="text-xs font-bold tracking-[0.18em] text-amber-600 uppercase">Yönetim Paneli</p>
              <h2 className="text-3xl font-bold text-slate-950 mt-2">Tekrar hoş geldiniz</h2>
              <p className="text-sm text-slate-500 mt-2">Devam etmek için yönetici şifrenizi girin.</p>
            </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="admin-password" className="block text-sm font-semibold text-slate-700 mb-2">Yönetici şifresi</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">●</span>
              <input id="admin-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Şifrenizi girin" required autoFocus autoComplete="current-password" className="w-full pl-10 pr-4 py-3.5 border border-slate-300 rounded-xl text-slate-950 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400" />
            </div>
          </div>

          {error && (
            <div role="alert" className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-slate-950 hover:bg-slate-800 disabled:bg-slate-400 text-white font-semibold rounded-xl transition-all shadow-lg shadow-slate-950/10"
          >
            {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
          </button>
        </form>
            <p className="text-center text-xs text-slate-400 mt-6">Yalnızca yetkili mağaza personeli içindir.</p>
          </div>
        </div>
      </section>
      </div>
  );
}

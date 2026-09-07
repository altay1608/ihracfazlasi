'use client';

import { useEffect, useState } from 'react';

interface DashboardData {
  totalProducts: number;
  totalSales: number;
  totalCategories: number;
  today: { sales: number; revenue: number; itemsSold: number };
  lowStock: { id: number; productName: string; sku: string; size: string | null; color: string | null; stock: number }[];
  recentSales: { id: number; date: string; total: number; items: number; paymentMethod: string | null }[];
}

function StatCard({
  title,
  value,
  sub,
  color,
}: {
  title: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className={`bg-white rounded-xl p-5 border-l-4 ${color} shadow-sm`}>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/admin/dashboard')
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setData(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-64">
        <div className="text-gray-400">Yükleniyor...</div>
      </div>
    );
  }

  if (!data) {
    return <div className="p-8 text-red-500">Veri alınamadı</div>;
  }

  const fmt = (n: number) =>
    new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }).format(n);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Bugün stats */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Bugün</h3>
        <div className="grid grid-cols-3 gap-4">
          <StatCard title="Satış Adedi" value={String(data.today.sales)} sub="işlem" color="border-indigo-500" />
          <StatCard title="Ciro" value={fmt(data.today.revenue)} sub="bugünkü gelir" color="border-green-500" />
          <StatCard title="Satılan Parça" value={String(data.today.itemsSold)} sub="adet" color="border-blue-500" />
        </div>
      </div>

      {/* Genel stats */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Genel</h3>
        <div className="grid grid-cols-3 gap-4">
          <StatCard title="Aktif Ürünler" value={String(data.totalProducts)} color="border-purple-500" />
          <StatCard title="Toplam Satış" value={String(data.totalSales)} sub="tüm zamanlar" color="border-orange-500" />
          <StatCard title="Kategoriler" value={String(data.totalCategories)} color="border-teal-500" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Düşük stok uyarıları */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="text-red-500">▲</span>
            Düşük Stok ({data.lowStock.length})
          </h3>
          {data.lowStock.length === 0 ? (
            <p className="text-sm text-gray-400">Düşük stoklu ürün yok</p>
          ) : (
            <div className="space-y-2">
              {data.lowStock.map((item) => (
                <div key={item.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{item.productName}</p>
                    <p className="text-xs text-gray-400">
                      {item.sku} {item.size ? `• ${item.size}` : ''} {item.color ? `• ${item.color}` : ''}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-bold px-2 py-1 rounded-full ${
                      item.stock === 0 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {item.stock} adet
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Son satışlar */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span className="text-green-500">●</span>
            Son Satışlar
          </h3>
          {data.recentSales.length === 0 ? (
            <p className="text-sm text-gray-400">Henüz satış yok</p>
          ) : (
            <div className="space-y-2">
              {data.recentSales.map((sale) => (
                <div key={sale.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">#{sale.id}</p>
                    <p className="text-xs text-gray-400">
                      {new Date(sale.date).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })}
                      {' • '}{sale.items} ürün
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">{fmt(sale.total)}</p>
                    <p className="text-xs text-gray-400">
                      {sale.paymentMethod === 'cash' ? 'Nakit' : sale.paymentMethod === 'card' ? 'Kart' : '-'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

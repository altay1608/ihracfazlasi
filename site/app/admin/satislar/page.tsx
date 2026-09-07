'use client';

import { useEffect, useState, useCallback } from 'react';

interface SaleItem {
  id: number;
  productName: string;
  size: string | null;
  color: string | null;
  quantity: number;
  unitPrice: number;
  variant?: { product: { name: string; sku: string } | null } | null;
}

interface Sale {
  id: number;
  saleDate: string;
  totalAmount: number;
  paymentMethod: string | null;
  source: string;
  notes: string | null;
  items: SaleItem[];
}

export default function SatislarPage() {
  const [sales, setSales] = useState<Sale[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [date, setDate] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const today = new Date().toISOString().split('T')[0];

  const fetchSales = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page) });
    if (date) params.set('date', date);
    fetch(`/api/admin/sales?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          setSales(res.data);
          setTotalPages(res.pagination.totalPages || 1);
        }
      })
      .finally(() => setLoading(false));
  }, [page, date]);

  useEffect(() => {
    fetchSales();
  }, [fetchSales]);

  const fmt = (n: number) =>
    new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(n);

  const paymentLabel = (m: string | null) => {
    if (m === 'cash') return 'Nakit';
    if (m === 'card') return 'Kart';
    return m || '—';
  };

  const totalRevenue = sales.reduce((s, sale) => s + sale.totalAmount, 0);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900">Satışlar</h2>
        {sales.length > 0 && (
          <div className="text-sm text-gray-500">
            Toplam:{' '}
            <span className="font-semibold text-gray-900">{fmt(totalRevenue)}</span>
            {date ? ` (${date})` : ''}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm mb-4">
        <div className="p-4 border-b border-gray-100 flex gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Tarih:</label>
            <input
              type="date"
              value={date}
              max={today}
              onChange={(e) => { setDate(e.target.value); setPage(1); }}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {date && (
            <button
              onClick={() => { setDate(''); setPage(1); }}
              className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg"
            >
              Temizle
            </button>
          )}
          <button
            onClick={() => { setDate(today); setPage(1); }}
            className="px-3 py-2 text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded-lg"
          >
            Bugün
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-400">Yükleniyor...</div>
        ) : sales.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Satış bulunamadı</div>
        ) : (
          <div>
            {sales.map((sale) => (
              <div key={sale.id} className="border-b border-gray-50 last:border-0">
                <div
                  className="flex items-center px-4 py-3 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === sale.id ? null : sale.id)}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-gray-900">#{sale.id}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(sale.saleDate).toLocaleString('tr-TR', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          sale.paymentMethod === 'cash'
                            ? 'bg-green-100 text-green-700'
                            : sale.paymentMethod === 'card'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {paymentLabel(sale.paymentMethod)}
                      </span>
                      <span className="text-xs text-gray-400">
                        {sale.items.reduce((s, i) => s + i.quantity, 0)} ürün
                      </span>
                    </div>
                    {sale.notes && (
                      <p className="text-xs text-gray-400 mt-1">{sale.notes}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-gray-900">{fmt(sale.totalAmount)}</p>
                    <p className="text-xs text-gray-400">{expandedId === sale.id ? '▲' : '▼'}</p>
                  </div>
                </div>

                {expandedId === sale.id && (
                  <div className="px-6 pb-4 bg-gray-50">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-gray-400 uppercase border-b border-gray-200">
                          <th className="text-left py-2">Ürün</th>
                          <th className="text-left py-2">Beden</th>
                          <th className="text-center py-2">Adet</th>
                          <th className="text-right py-2">Birim Fiyat</th>
                          <th className="text-right py-2">Toplam</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sale.items.map((item) => (
                          <tr key={item.id} className="border-b border-gray-200 last:border-0">
                            <td className="py-2 font-medium">{item.productName}</td>
                            <td className="py-2 text-gray-500">
                              {item.size || '—'} {item.color ? `/ ${item.color}` : ''}
                            </td>
                            <td className="py-2 text-center">{item.quantity}</td>
                            <td className="py-2 text-right">{fmt(item.unitPrice)}</td>
                            <td className="py-2 text-right font-medium">
                              {fmt(item.unitPrice * item.quantity)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="p-4 flex items-center justify-between border-t border-gray-100">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
            >
              ← Önceki
            </button>
            <span className="text-sm text-gray-500">
              {page} / {totalPages}
            </span>
            <button
              disabled={page === totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
            >
              Sonraki →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

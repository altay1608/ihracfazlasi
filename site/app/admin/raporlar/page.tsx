'use client';

import { useEffect, useState, useCallback } from 'react';

interface ReportData {
  date: string;
  summary: {
    totalSales: number;
    totalRevenue: number;
    totalProfit: number;
    totalItemsSold: number;
  };
  paymentBreakdown: { cash: number; card: number };
  topProducts: { sku: string; name: string; quantitySold: number; revenue: number }[];
  sales: { id: number; time: string; amount: number; items: number }[];
}

export default function RaporlarPage() {
  const today = new Date().toISOString().split('T')[0];
  const [date, setDate] = useState(today);
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchReport = useCallback(() => {
    setLoading(true);
    fetch(`/api/v1/reports/daily?date=${date}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setReport(res.data);
      })
      .finally(() => setLoading(false));
  }, [date]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const fmt = (n: number) =>
    new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(n);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Raporlar</h2>
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={date}
            max={today}
            onChange={(e) => setDate(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={() => setDate(today)}
            className="px-3 py-2 text-sm text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50"
          >
            Bugün
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-gray-400">Yükleniyor...</div>
      ) : !report ? (
        <div className="p-12 text-center text-gray-400">Rapor oluşturulamadı</div>
      ) : (
        <>
          {/* Özet */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Satış Sayısı', value: String(report.summary.totalSales), sub: 'işlem' },
              { label: 'Toplam Ciro', value: fmt(report.summary.totalRevenue), sub: 'gelir' },
              { label: 'Tahmini Kar', value: fmt(report.summary.totalProfit), sub: 'kar' },
              { label: 'Satılan Parça', value: String(report.summary.totalItemsSold), sub: 'adet' },
            ].map((card) => (
              <div key={card.label} className="bg-white rounded-xl p-5 shadow-sm">
                <p className="text-xs text-gray-400 uppercase font-medium">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
                <p className="text-xs text-gray-400">{card.sub}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Ödeme dağılımı */}
            <div className="bg-white rounded-xl shadow-sm p-5">
              <h3 className="font-semibold text-gray-800 mb-4">Ödeme Yöntemi</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-green-500 inline-block" />
                    <span className="text-sm text-gray-600">Nakit</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">
                    {fmt(report.paymentBreakdown.cash)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" />
                    <span className="text-sm text-gray-600">Kredi Kartı</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">
                    {fmt(report.paymentBreakdown.card)}
                  </span>
                </div>
                {(report.paymentBreakdown.cash + report.paymentBreakdown.card) > 0 && (
                  <div className="pt-2 mt-2 border-t border-gray-100">
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full"
                        style={{
                          width: `${
                            (report.paymentBreakdown.cash /
                              (report.paymentBreakdown.cash + report.paymentBreakdown.card)) *
                            100
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Satış listesi */}
            <div className="bg-white rounded-xl shadow-sm p-5">
              <h3 className="font-semibold text-gray-800 mb-4">
                Günlük Satışlar ({report.sales.length})
              </h3>
              {report.sales.length === 0 ? (
                <p className="text-sm text-gray-400">Bu gün satış yok</p>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {report.sales.map((sale) => (
                    <div key={sale.id} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">{sale.time}</span>
                        <span className="text-xs text-gray-600">#{sale.id}</span>
                        <span className="text-xs text-gray-400">{sale.items} ürün</span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">{fmt(sale.amount)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* En çok satan ürünler */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h3 className="font-semibold text-gray-800 mb-4">En Çok Satan Ürünler</h3>
            {report.topProducts.length === 0 ? (
              <p className="text-sm text-gray-400">Veri yok</p>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-gray-400 uppercase border-b border-gray-100">
                    <th className="text-left py-2">Ürün</th>
                    <th className="text-left py-2">SKU</th>
                    <th className="text-right py-2">Adet</th>
                    <th className="text-right py-2">Ciro</th>
                  </tr>
                </thead>
                <tbody>
                  {report.topProducts.map((p, i) => (
                    <tr key={p.sku} className="border-b border-gray-50 last:border-0">
                      <td className="py-2.5 flex items-center gap-2">
                        <span className="text-xs font-bold text-gray-400 w-5">{i + 1}.</span>
                        <span className="text-sm text-gray-800">{p.name}</span>
                      </td>
                      <td className="py-2.5 text-xs text-gray-400 font-mono">{p.sku}</td>
                      <td className="py-2.5 text-right text-sm font-semibold text-gray-900">
                        {p.quantitySold}
                      </td>
                      <td className="py-2.5 text-right text-sm font-semibold text-gray-900">
                        {fmt(p.revenue)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

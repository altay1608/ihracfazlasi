export default function LoadingProducts() {
  return (
    <section className="section-sm container-wide" aria-busy="true" aria-label="Ürünler yükleniyor">
      <p role="status" className="mb-6 text-gray-500">Ürünler yükleniyor…</p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="aspect-[3/4] rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    </section>
  );
}

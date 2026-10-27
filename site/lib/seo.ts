/** Escape database text before embedding JSON in an HTML script element. */
export function serializeJsonLd(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

export function pageNumber(value?: string): number {
  const page = Number(value || "1");
  return Number.isSafeInteger(page) && page > 0 && page <= 100000 ? page : 1;
}

export function categoryIntro(slug: string, name: string): string {
  const descriptions: Record<string, string> = {
    "ust-giyim": "Erkek üst giyim koleksiyonunda tişört, gömlek, triko ve ceket seçeneklerini inceleyin. Ürün sayfalarında fiyat, fotoğraf ve mevcut bedenleri karşılaştırabilir; kalıp ve ölçü için WhatsApp üzerinden bilgi alabilirsiniz. Bursa İnegöl mağazamızda ürünleri yakından görebilirsiniz.",
    "alt-giyim": "Erkek pantolon, jean ve şort seçeneklerini alt giyim koleksiyonunda keşfedin. Bel bedeni ve kalıp ürüne göre değişebilir; seçim yaparken ürünün mevcut bedenlerini kontrol edin. Ölçü ve kombin sorularınızı WhatsApp üzerinden iletebilir veya Bursa İnegöl mağazamızı ziyaret edebilirsiniz.",
    "aksesuar": "Günlük kombinlerinizi tamamlayacak aksesuarları inceleyin. Mevcut ürünlerin fotoğraf ve fiyatlarını ürün sayfalarında görebilir, ölçü ve kullanım detaylarını WhatsApp üzerinden sorabilirsiniz. İhraç Fazlası Giyim İnegöl mağazamızdaki güncel seçenekler bu koleksiyonda yer alır.",
  };
  return descriptions[slug] || `${name} koleksiyonundaki güncel ürünleri, fiyatları ve mevcut seçenekleri inceleyin. Ürün detayları için WhatsApp üzerinden bilgi alabilir veya Bursa İnegöl mağazamızı ziyaret edebilirsiniz.`;
}

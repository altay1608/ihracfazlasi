// Site bilgileri
const getBaseUrl = () => {
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  if (process.env.NEXT_PUBLIC_SITE_URL) return process.env.NEXT_PUBLIC_SITE_URL;
  return "";
};

export const SITE_CONFIG = {
  name: "İhraç Fazlası Giyim İnegöl",
  shortName: "İhraç Fazlası Giyim",
  description: "Bursa İnegöl'de Prada, Lacoste, Tommy Hilfiger, Hugo Boss erkek giyim. İhraç fazlası ithal ürünler.",
  url: getBaseUrl(),
};

// Mağaza Bilgileri
export const STORE_INFO = {
  name: "İhraç Fazlası Giyim İnegöl",
  address: "Ertuğrulgazi, Kozluca Yolu 13/AA, 16400 İnegöl/Bursa",
  city: "İnegöl",
  region: "Bursa",
  country: "Türkiye",
  postalCode: "16400",
  phone: "0538 479 36 96",
  phoneClean: "+905384793696",
  hours: "10:00 - 22:00",
  openingHours: "Mo-Su 10:00-22:00",
  googleRating: 5.0,
  googleReviews: 58,
  coordinates: {
    lat: 40.0781,
    lng: 29.5126,
  },
};

// Dünya Markaları
export const BRANDS = [
  "Prada",
  "Lacoste",
  "Tommy Hilfiger",
  "Hugo Boss",
  "Armani",
  "Versace",
  "Calvin Klein",
  "Ralph Lauren",
  "Gucci",
  "Burberry",
];

// WhatsApp
export const WHATSAPP_PHONE = process.env.NEXT_PUBLIC_WHATSAPP_PHONE || "905384793696";

// Navigasyon linkleri
export const NAV_LINKS = [
  { href: "/", label: "Ana Sayfa" },
  { href: "/urunler", label: "Ürünler" },
  { href: "/hakkimizda", label: "Hakkımızda" },
];

// Kategoriler (3 ana kategori)
export const DEFAULT_CATEGORIES = [
  { name: "Üst Giyim", slug: "ust-giyim" },
  { name: "Alt Giyim", slug: "alt-giyim" },
  { name: "Aksesuar", slug: "aksesuar" },
];

// Bedenler - Kategori bazlı
export const SIZES = ["S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]; // Eski format (geriye uyumluluk)

export const SIZES_BY_CATEGORY = {
  "ust-giyim": ["S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"],
  "alt-giyim": ["28", "30", "32", "34", "36", "38", "40", "42"],
  "aksesuar": ["STD"],
};

export const SIZE_TYPE = {
  UST_GIYIM: "ust-giyim",
  ALT_GIYIM: "alt-giyim",
  AKSESUAR: "aksesuar",
} as const;

// Ürün tipi → Beden tipi eşleşmesi
export const PRODUCT_TYPE_TO_SIZE_TYPE: Record<string, keyof typeof SIZES_BY_CATEGORY> = {
  // Üst giyim
  "t-shirt": "ust-giyim",
  "tişört": "ust-giyim",
  "polo": "ust-giyim",
  "gömlek": "ust-giyim",
  "kazak": "ust-giyim",
  "triko": "ust-giyim",
  "sweatshirt": "ust-giyim",
  "hoodie": "ust-giyim",
  "ceket": "ust-giyim",
  "mont": "ust-giyim",
  "blazer": "ust-giyim",
  "yelek": "ust-giyim",
  "hırka": "ust-giyim",
  // Alt giyim
  "pantolon": "alt-giyim",
  "jean": "alt-giyim",
  "jeans": "alt-giyim",
  "kot": "alt-giyim",
  "şort": "alt-giyim",
  "bermuda": "alt-giyim",
  "eşofman altı": "alt-giyim",
  "jogger": "alt-giyim",
  "chino": "alt-giyim",
  // Aksesuar
  "kemer": "aksesuar",
  "çanta": "aksesuar",
  "cüzdan": "aksesuar",
  "şapka": "aksesuar",
  "atkı": "aksesuar",
  "eldiven": "aksesuar",
  "kravat": "aksesuar",
  "saat": "aksesuar",
  "gözlük": "aksesuar",
};

// Renkler (Türkçe)
export const COLORS = [
  { name: "Siyah", value: "#000000" },
  { name: "Beyaz", value: "#FFFFFF" },
  { name: "Kırmızı", value: "#DC2626" },
  { name: "Mavi", value: "#2563EB" },
  { name: "Yeşil", value: "#16A34A" },
  { name: "Sarı", value: "#EAB308" },
  { name: "Turuncu", value: "#EA580C" },
  { name: "Mor", value: "#9333EA" },
  { name: "Pembe", value: "#EC4899" },
  { name: "Gri", value: "#6B7280" },
  { name: "Lacivert", value: "#1E3A5F" },
  { name: "Bej", value: "#D4C4B0" },
  { name: "Kahverengi", value: "#78350F" },
  { name: "Bordo", value: "#7F1D1D" },
];

// Sıralama seçenekleri
export const SORT_OPTIONS = [
  { value: "newest", label: "En Yeni" },
  { value: "price-asc", label: "Fiyat: Düşükten Yükseğe" },
  { value: "price-desc", label: "Fiyat: Yüksekten Düşüğe" },
  { value: "name-asc", label: "A-Z" },
  { value: "name-desc", label: "Z-A" },
];

// Ödeme yöntemleri
export const PAYMENT_METHODS = [
  { value: "cash", label: "Nakit" },
  { value: "card", label: "Kredi Kartı" },
];

// Stok değişim nedenleri
export const STOCK_CHANGE_REASONS = [
  { value: "sale", label: "Satış" },
  { value: "restock", label: "Yeni Stok" },
  { value: "adjustment", label: "Düzeltme" },
  { value: "return", label: "İade" },
];

// Düşük stok eşiği
export const LOW_STOCK_THRESHOLD = 3;

// API limitleri
export const API_LIMITS = {
  productsPerPage: 50,
  salesPerPage: 20,
  maxImageSize: 5 * 1024 * 1024, // 5MB
  allowedImageTypes: ["image/jpeg", "image/png", "image/webp"],
};

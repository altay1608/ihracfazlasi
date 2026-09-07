import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Tailwind class birleştirme
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Slug oluşturma (Türkçe karakter desteği)
export function slugify(text: string): string {
  const turkishMap: Record<string, string> = {
    ç: "c",
    Ç: "C",
    ğ: "g",
    Ğ: "G",
    ı: "i",
    İ: "I",
    ö: "o",
    Ö: "O",
    ş: "s",
    Ş: "S",
    ü: "u",
    Ü: "U",
  };

  return text
    .split("")
    .map((char) => turkishMap[char] || char)
    .join("")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

// Fiyat formatlama
export function formatPrice(price: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

// Tarih formatlama
export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(date));
}

export function formatDateTime(date: Date | string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function formatTime(date: Date | string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

// WhatsApp link oluşturma
export function createWhatsAppLink(phoneNumber: string, message: string): string {
  const encodedMessage = encodeURIComponent(message);
  return `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
}

// Stok durumu mesajı
export function getStockStatus(stock: number): {
  text: string;
  color: "success" | "warning" | "error";
} {
  if (stock > 5) {
    return { text: "Stokta", color: "success" };
  } else if (stock > 1) {
    return { text: `Son ${stock} adet`, color: "warning" };
  } else if (stock === 1) {
    return { text: "Tükenmek Üzere", color: "error" };
  } else {
    return { text: "Tükendi", color: "error" };
  }
}

// Beden sıralama
export function sortSizes(sizes: string[]): string[] {
  const sizeOrder: Record<string, number> = {
    XXS: 1,
    XS: 2,
    S: 3,
    M: 4,
    L: 5,
    XL: 6,
    XXL: 7,
    "3XL": 8,
    XXXL: 8,
    "4XL": 9,
    "5XL": 10,
    "6XL": 11,
  };

  return sizes.sort((a, b) => {
    const aUpper = a.toUpperCase();
    const bUpper = b.toUpperCase();
    const aOrder = sizeOrder[aUpper] || parseInt(a) || 999;
    const bOrder = sizeOrder[bUpper] || parseInt(b) || 999;
    return aOrder - bOrder;
  });
}

// Benzersiz değerler (variants'dan renk/beden çıkarma)
export function getUniqueValues<T, K extends keyof T>(
  items: T[],
  key: K
): NonNullable<T[K]>[] {
  const values = items
    .map((item) => item[key])
    .filter((value): value is NonNullable<T[K]> => value != null);
  return [...new Set(values)];
}

// Debounce (arama için)
export function debounce<T extends (...args: Parameters<T>) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

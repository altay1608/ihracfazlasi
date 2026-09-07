"use client";

import Link from "next/link";
import Image from "next/image";
import { useRecentlyViewed } from "@/hooks/useRecentlyViewed";
import { formatPrice } from "@/lib/utils";

interface RecentlyViewedProps {
  excludeId?: number;
  title?: string;
}

export default function RecentlyViewed({ excludeId, title = "Son Baktiklariniz" }: RecentlyViewedProps) {
  const { recentProducts, isLoaded } = useRecentlyViewed();

  const filteredProducts = excludeId
    ? recentProducts.filter((p) => p.id !== excludeId)
    : recentProducts;

  if (!isLoaded || filteredProducts.length === 0) {
    return null;
  }

  return (
    <section className="py-12 border-t border-gray-100 dark:border-gray-800">
      <div className="container-wide">
        <h2 className="text-xl font-semibold text-foreground dark:text-white mb-6">
          {title}
        </h2>

        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
          {filteredProducts.map((product) => (
            <Link
              key={product.id}
              href={`/urunler/${product.slug}`}
              className="group flex-shrink-0 w-40"
            >
              <div className="relative aspect-square bg-gray-100 dark:bg-gray-800 rounded-xl overflow-hidden mb-2">
                {product.primaryImage ? (
                  <Image
                    src={product.primaryImage}
                    alt={product.name}
                    fill
                    sizes="160px"
                    className="object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor" className="w-10 h-10">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                    </svg>
                  </div>
                )}
              </div>
              <h3 className="text-sm font-medium text-foreground dark:text-white line-clamp-2 group-hover:text-accent transition-colors">
                {product.name}
              </h3>
              <p className="text-sm font-semibold text-foreground dark:text-white mt-1">
                {formatPrice(product.price)}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

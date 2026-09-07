"use client";

import Link from "next/link";
import Image from "next/image";
import { useFavorites } from "@/hooks/useFavorites";
import { formatPrice } from "@/lib/utils";

export default function FavorilerPage() {
  const { favorites, isLoaded, removeFavorite, clearFavorites } = useFavorites();

  if (!isLoaded) {
    return (
      <div className="container-wide py-12">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-8" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="aspect-[3/4] bg-gray-200 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container-wide py-8 md:py-12">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold text-foreground">
            Favorilerim
          </h1>
          <p className="text-gray-500 mt-1">
            {favorites.count > 0
              ? `${favorites.count} urun favorilerinizde`
              : "Henuz favori urun eklemediniz"}
          </p>
        </div>

        {favorites.count > 0 && (
          <button
            onClick={() => {
              if (confirm("Tum favorileri silmek istediginize emin misiniz?")) {
                clearFavorites();
              }
            }}
            className="text-sm text-gray-500 hover:text-red-500 transition-colors"
          >
            Tumunu Temizle
          </button>
        )}
      </div>

      {/* Empty State */}
      {favorites.count === 0 && (
        <div className="text-center py-16">
          <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
              className="w-12 h-12 text-gray-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-medium text-foreground mb-2">
            Favori listeniz bos
          </h2>
          <p className="text-gray-500 mb-6">
            Begendginiz urunleri favorilere ekleyerek daha sonra kolayca ulasabilirsiniz.
          </p>
          <Link
            href="/urunler"
            className="inline-flex items-center gap-2 px-6 py-3 bg-foreground text-white rounded-full hover:bg-gray-800 transition-colors"
          >
            Urunlere Goz At
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-4 h-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </Link>
        </div>
      )}

      {/* Favorites Grid */}
      {favorites.count > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
          {favorites.items.map((product) => (
            <div key={product.id} className="group relative">
              <Link href={`/urunler/${product.slug}`} className="block">
                {/* Image */}
                <div className="relative aspect-[3/4] bg-gray-100 rounded-xl overflow-hidden mb-3">
                  {product.primaryImage ? (
                    <Image
                      src={product.primaryImage}
                      alt={product.name}
                      fill
                      sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
                      className="object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1}
                        stroke="currentColor"
                        className="w-12 h-12"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                        />
                      </svg>
                    </div>
                  )}

                  {/* Remove Button */}
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      removeFavorite(product.id);
                    }}
                    className="absolute top-2 right-2 w-8 h-8 flex items-center justify-center bg-white/90 backdrop-blur-sm rounded-full shadow-sm hover:bg-red-50 hover:scale-110 transition-all"
                    aria-label="Favorilerden cikar"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="w-4 h-4 text-red-500"
                    >
                      <path
                        d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
                      />
                    </svg>
                  </button>
                </div>

                {/* Info */}
                <div className="space-y-1">
                  <p className="text-xs text-gray-500">{product.sku}</p>
                  <h3 className="text-sm font-medium text-foreground line-clamp-2 group-hover:text-accent transition-colors">
                    {product.name}
                  </h3>
                  <p className="text-sm font-semibold text-foreground">
                    {formatPrice(product.price)}
                  </p>
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

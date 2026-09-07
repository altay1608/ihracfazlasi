"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { formatPrice, slugify, sortSizes } from "@/lib/utils";
import { useCart } from "@/hooks/useCart";
import { useFavorites } from "@/hooks/useFavorites";
import type { Product } from "@/types";

interface QuickViewProps {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function QuickView({ product, isOpen, onClose }: QuickViewProps) {
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState(0);
  const { addItem: addToCart } = useCart();
  const { isFavorite, toggleFavorite } = useFavorites();

  // Reset state when product changes
  useEffect(() => {
    setSelectedSize(null);
    setSelectedImage(0);
  }, [product?.id]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!product) return null;

  const availableSizes = product.variants
    ?.filter((v) => v.stock > 0)
    .map((v) => v.size)
    .filter(Boolean) as string[];
  const uniqueSizes = sortSizes([...new Set(availableSizes)]);

  const images = product.images || [];
  const primaryImage = product.primaryImage || images[0]?.imageUrl;
  const slug = slugify(product.name);
  const isFav = isFavorite(product.id);

  const handleAddToCart = () => {
    if (!selectedSize) return;
    const variant = product.variants?.find((v) => v.size === selectedSize && v.stock > 0);
    if (!variant) return;

    addToCart({
      productId: product.id,
      sku: product.sku,
      name: product.name,
      size: selectedSize,
      color: variant.color || null,
      price: product.price,
      image: primaryImage || "/placeholder-product.jpg",
      quantity: 1,
      maxStock: variant.stock,
    });

    onClose();
  };

  const handleFavorite = () => {
    toggleFavorite({
      id: product.id,
      sku: product.sku,
      name: product.name,
      price: product.price,
      primaryImage,
      slug: `${slug}-${product.id}`,
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 z-50 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden md:max-w-3xl md:w-full md:max-h-[85vh]"
          >
            {/* Close Button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 z-10 w-10 h-10 flex items-center justify-center bg-white/90 dark:bg-gray-800/90 rounded-full shadow-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <div className="flex flex-col md:flex-row h-full overflow-y-auto">
              {/* Image */}
              <div className="md:w-1/2 p-4 md:p-6">
                <div className="relative aspect-square bg-gray-100 dark:bg-gray-800 rounded-xl overflow-hidden">
                  {primaryImage ? (
                    <Image
                      src={images[selectedImage]?.imageUrl || primaryImage}
                      alt={product.name}
                      fill
                      className="object-cover"
                      sizes="(max-width: 768px) 100vw, 50vw"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor" className="w-20 h-20">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Thumbnails */}
                {images.length > 1 && (
                  <div className="flex gap-2 mt-3 overflow-x-auto">
                    {images.slice(0, 4).map((img, idx) => (
                      <button
                        key={img.id}
                        onClick={() => setSelectedImage(idx)}
                        className={`relative flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden ${
                          selectedImage === idx ? "ring-2 ring-accent" : "opacity-60 hover:opacity-100"
                        }`}
                      >
                        <Image
                          src={img.imageUrl}
                          alt={`${product.name} ${idx + 1}`}
                          fill
                          className="object-cover"
                          sizes="64px"
                        />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="md:w-1/2 p-4 md:p-6 flex flex-col">
                <div className="flex-1">
                  <p className="text-sm text-gray-500 mb-1">{product.sku}</p>
                  <h2 className="text-xl font-semibold text-foreground dark:text-white mb-2">
                    {product.name}
                  </h2>
                  <p className="text-2xl font-bold text-foreground dark:text-white mb-6">
                    {formatPrice(product.price)}
                  </p>

                  {/* Sizes */}
                  {uniqueSizes.length > 0 && (
                    <div className="mb-6">
                      <p className="text-sm font-medium text-foreground dark:text-white mb-3">Beden Secin</p>
                      <div className="flex flex-wrap gap-2">
                        {uniqueSizes.map((size) => (
                          <button
                            key={size}
                            onClick={() => setSelectedSize(size)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                              selectedSize === size
                                ? "bg-foreground text-white dark:bg-white dark:text-foreground"
                                : "bg-gray-100 dark:bg-gray-800 text-foreground dark:text-white hover:bg-gray-200 dark:hover:bg-gray-700"
                            }`}
                          >
                            {size}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={handleAddToCart}
                    disabled={!selectedSize}
                    className="flex-1 py-3 bg-foreground dark:bg-white text-white dark:text-foreground font-medium rounded-full hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {selectedSize ? "Sepete Ekle" : "Beden Secin"}
                  </button>
                  <button
                    onClick={handleFavorite}
                    className="w-12 h-12 flex items-center justify-center border border-gray-200 dark:border-gray-700 rounded-full hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill={isFav ? "currentColor" : "none"}
                      stroke="currentColor"
                      strokeWidth={isFav ? 0 : 1.5}
                      className={`w-5 h-5 ${isFav ? "text-red-500" : ""}`}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                    </svg>
                  </button>
                </div>

                {/* View Full Details Link */}
                <Link
                  href={`/urunler/${slug}-${product.id}`}
                  onClick={onClose}
                  className="block mt-4 text-center text-sm text-accent hover:underline"
                >
                  Tum Detaylari Gor
                </Link>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

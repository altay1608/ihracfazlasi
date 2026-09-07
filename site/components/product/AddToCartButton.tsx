"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCart } from "@/hooks/useCart";
import { formatPrice, getStockStatus, sortSizes, getUniqueValues } from "@/lib/utils";
import type { Product, ProductVariant } from "@/types";

interface AddToCartButtonProps {
  product: Product;
}

export default function AddToCartButton({ product }: AddToCartButtonProps) {
  const { addItem, isInCart } = useCart();
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [selectedColor, setSelectedColor] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [showSuccess, setShowSuccess] = useState(false);

  const variants = product.variants || [];

  // Get unique sizes and colors
  const sizes = sortSizes(getUniqueValues(variants, "size").filter(Boolean) as string[]);
  const colors = getUniqueValues(variants, "color").filter(Boolean) as string[];

  // Find selected variant
  const selectedVariant = variants.find(
    (v) =>
      (sizes.length === 0 || v.size === selectedSize) &&
      (colors.length === 0 || v.color === selectedColor)
  );

  const stock = selectedVariant?.stock || 0;
  const stockStatus = getStockStatus(stock);
  const isOutOfStock = stock === 0;
  const alreadyInCart = selectedVariant
    ? isInCart(product.id, selectedVariant.size || undefined, selectedVariant.color || undefined)
    : false;

  // Check if size/color combination has stock
  const hasStock = (size?: string, color?: string) => {
    return variants.some(
      (v) =>
        (size === undefined || v.size === size) &&
        (color === undefined || v.color === color) &&
        v.stock > 0
    );
  };

  const handleAddToCart = () => {
    if (!selectedVariant || isOutOfStock) return;

    const primaryImage =
      product.images?.find((img) => img.isPrimary)?.imageUrl ||
      product.images?.[0]?.imageUrl ||
      "";

    addItem({
      productId: product.id,
      sku: product.sku,
      name: product.name,
      size: selectedVariant.size,
      color: selectedVariant.color,
      price: product.price,
      quantity,
      image: primaryImage,
      maxStock: selectedVariant.stock,
    });

    setShowSuccess(true);
    setTimeout(() => setShowSuccess(false), 2000);
  };

  // Auto-select if only one option
  if (sizes.length === 1 && !selectedSize) {
    setSelectedSize(sizes[0]);
  }
  if (colors.length === 1 && !selectedColor) {
    setSelectedColor(colors[0]);
  }

  const canAddToCart =
    (sizes.length === 0 || selectedSize) &&
    (colors.length === 0 || selectedColor) &&
    !isOutOfStock &&
    selectedVariant;

  return (
    <div className="space-y-6">
      {/* Size Selector */}
      {sizes.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-body font-medium text-foreground">Beden</label>
            {selectedSize && (
              <span className="text-caption text-gray-500">{selectedSize} seçildi</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {sizes.map((size) => {
              const available = hasStock(size, selectedColor || undefined);
              return (
                <button
                  key={size}
                  onClick={() => setSelectedSize(size)}
                  disabled={!available}
                  className={`min-w-[48px] px-4 py-3 rounded-apple-sm text-sm font-medium transition-all ${
                    selectedSize === size
                      ? "bg-foreground text-white"
                      : available
                      ? "bg-gray-100 text-foreground hover:bg-gray-200"
                      : "bg-gray-50 text-gray-300 cursor-not-allowed line-through"
                  }`}
                >
                  {size}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Color Selector */}
      {colors.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-body font-medium text-foreground">Renk</label>
            {selectedColor && (
              <span className="text-caption text-gray-500">{selectedColor}</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {colors.map((color) => {
              const available = hasStock(selectedSize || undefined, color);
              return (
                <button
                  key={color}
                  onClick={() => setSelectedColor(color)}
                  disabled={!available}
                  className={`px-4 py-3 rounded-apple-sm text-sm font-medium transition-all ${
                    selectedColor === color
                      ? "bg-foreground text-white"
                      : available
                      ? "bg-gray-100 text-foreground hover:bg-gray-200"
                      : "bg-gray-50 text-gray-300 cursor-not-allowed"
                  }`}
                >
                  {color}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Stock Status */}
      {selectedVariant && (
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              stockStatus.color === "success"
                ? "bg-success"
                : stockStatus.color === "warning"
                ? "bg-amber-500"
                : "bg-red-500"
            }`}
          />
          <span
            className={`text-sm ${
              stockStatus.color === "success"
                ? "text-success"
                : stockStatus.color === "warning"
                ? "text-amber-600"
                : "text-red-500"
            }`}
          >
            {stockStatus.text}
          </span>
        </div>
      )}

      {/* Quantity Selector */}
      {canAddToCart && !isOutOfStock && (
        <div>
          <label className="text-body font-medium text-foreground block mb-3">Adet</label>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center hover:bg-gray-200 transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-4 h-4"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15" />
              </svg>
            </button>
            <span className="w-12 text-center text-lg font-medium">{quantity}</span>
            <button
              onClick={() => setQuantity((q) => Math.min(stock, q + 1))}
              disabled={quantity >= stock}
              className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-4 h-4"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Price */}
      <div className="pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-body text-gray-500">Toplam</span>
          <span className="text-title text-foreground">{formatPrice(product.price * quantity)}</span>
        </div>
      </div>

      {/* Add to Cart Button */}
      <button
        onClick={handleAddToCart}
        disabled={!canAddToCart}
        className={`w-full py-4 rounded-full text-lg font-medium transition-all ${
          canAddToCart
            ? "bg-foreground text-white hover:bg-gray-800 active:scale-[0.98]"
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        }`}
      >
        {isOutOfStock
          ? "Stokta Yok"
          : !selectedSize && sizes.length > 0
          ? "Beden Seçin"
          : !selectedColor && colors.length > 0
          ? "Renk Seçin"
          : alreadyInCart
          ? "Sepete Daha Fazla Ekle"
          : "Sepete Ekle"}
      </button>

      {/* Success Message */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center justify-center gap-2 text-success"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-5 h-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            <span>Sepete eklendi!</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

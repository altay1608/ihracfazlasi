"use client";

import { useState, useEffect, useCallback } from "react";
import type { CartItem, CartState } from "@/types";

const CART_STORAGE_KEY = "ihrac-fazlasi-cart";

function getInitialCart(): CartState {
  if (typeof window === "undefined") {
    return { items: [], totalItems: 0, totalPrice: 0 };
  }

  try {
    const stored = localStorage.getItem(CART_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return calculateTotals(parsed.items || []);
    }
  } catch {
    // localStorage error
  }

  return { items: [], totalItems: 0, totalPrice: 0 };
}

function calculateTotals(items: CartItem[]): CartState {
  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalPrice = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  return { items, totalItems, totalPrice };
}

export function useCart() {
  const [cart, setCart] = useState<CartState>({ items: [], totalItems: 0, totalPrice: 0 });
  const [isLoaded, setIsLoaded] = useState(false);

  // İlk yüklemede localStorage'dan oku
  useEffect(() => {
    setCart(getInitialCart());
    setIsLoaded(true);
  }, []);

  // Değişiklikleri localStorage'a kaydet
  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    }
  }, [cart, isLoaded]);

  // Sepete ürün ekle
  const addItem = useCallback((item: Omit<CartItem, "id">) => {
    setCart((prev) => {
      const id = `${item.productId}-${item.size || "nosize"}-${item.color || "nocolor"}`;
      const existingIndex = prev.items.findIndex((i) => i.id === id);

      let newItems: CartItem[];

      if (existingIndex >= 0) {
        // Mevcut ürünün miktarını artır
        newItems = prev.items.map((i, idx) =>
          idx === existingIndex
            ? { ...i, quantity: Math.min(i.quantity + item.quantity, i.maxStock) }
            : i
        );
      } else {
        // Yeni ürün ekle
        newItems = [...prev.items, { ...item, id }];
      }

      return calculateTotals(newItems);
    });
  }, []);

  // Ürün miktarını güncelle
  const updateQuantity = useCallback((id: string, quantity: number) => {
    setCart((prev) => {
      if (quantity <= 0) {
        return calculateTotals(prev.items.filter((i) => i.id !== id));
      }

      const newItems = prev.items.map((item) =>
        item.id === id ? { ...item, quantity: Math.min(quantity, item.maxStock) } : item
      );

      return calculateTotals(newItems);
    });
  }, []);

  // Ürünü sepetten çıkar
  const removeItem = useCallback((id: string) => {
    setCart((prev) => calculateTotals(prev.items.filter((i) => i.id !== id)));
  }, []);

  // Sepeti temizle
  const clearCart = useCallback(() => {
    setCart({ items: [], totalItems: 0, totalPrice: 0 });
  }, []);

  // Ürün sepette mi kontrol et
  const isInCart = useCallback(
    (productId: number, size?: string, color?: string) => {
      const id = `${productId}-${size || "nosize"}-${color || "nocolor"}`;
      return cart.items.some((item) => item.id === id);
    },
    [cart.items]
  );

  // Sepetteki ürün adedini al
  const getItemQuantity = useCallback(
    (productId: number, size?: string, color?: string) => {
      const id = `${productId}-${size || "nosize"}-${color || "nocolor"}`;
      const item = cart.items.find((i) => i.id === id);
      return item?.quantity || 0;
    },
    [cart.items]
  );

  return {
    cart,
    isLoaded,
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
    isInCart,
    getItemQuantity,
  };
}

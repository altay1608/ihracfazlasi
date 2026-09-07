"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "ihrac-fazlasi-recently-viewed";
const MAX_ITEMS = 10;

export interface RecentProduct {
  id: number;
  sku: string;
  name: string;
  price: number;
  primaryImage?: string | null;
  slug: string;
  viewedAt: number;
}

export function useRecentlyViewed() {
  const [recentProducts, setRecentProducts] = useState<RecentProduct[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const items = JSON.parse(stored) as RecentProduct[];
        setRecentProducts(items);
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
    setIsLoaded(true);
  }, []);

  // Save to localStorage
  const saveRecent = useCallback((items: RecentProduct[]) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    setRecentProducts(items);
  }, []);

  // Add product to recently viewed
  const addRecentProduct = useCallback((product: Omit<RecentProduct, "viewedAt">) => {
    setRecentProducts((prev) => {
      // Remove if already exists
      const filtered = prev.filter((item) => item.id !== product.id);

      // Add to beginning
      const newItem: RecentProduct = {
        ...product,
        viewedAt: Date.now(),
      };
      const newItems = [newItem, ...filtered].slice(0, MAX_ITEMS);

      saveRecent(newItems);
      return newItems;
    });
  }, [saveRecent]);

  // Clear history
  const clearHistory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setRecentProducts([]);
  }, []);

  return {
    recentProducts,
    isLoaded,
    addRecentProduct,
    clearHistory,
  };
}

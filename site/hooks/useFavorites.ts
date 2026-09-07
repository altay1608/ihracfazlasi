"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "ihrac-fazlasi-favorites";

export interface FavoriteProduct {
  id: number;
  sku: string;
  name: string;
  price: number;
  primaryImage?: string | null;
  slug: string;
  addedAt: number;
}

export interface FavoritesState {
  items: FavoriteProduct[];
  count: number;
}

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoritesState>({ items: [], count: 0 });
  const [isLoaded, setIsLoaded] = useState(false);

  // Load from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const items = JSON.parse(stored) as FavoriteProduct[];
        setFavorites({ items, count: items.length });
      }
    } catch {
      // Invalid data, reset
      localStorage.removeItem(STORAGE_KEY);
    }
    setIsLoaded(true);
  }, []);

  // Save to localStorage
  const saveFavorites = useCallback((items: FavoriteProduct[]) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    setFavorites({ items, count: items.length });
  }, []);

  // Add to favorites
  const addFavorite = useCallback((product: Omit<FavoriteProduct, "addedAt">) => {
    setFavorites((prev) => {
      const exists = prev.items.some((item) => item.id === product.id);
      if (exists) return prev;

      const newItem: FavoriteProduct = {
        ...product,
        addedAt: Date.now(),
      };
      const newItems = [newItem, ...prev.items];
      saveFavorites(newItems);
      return { items: newItems, count: newItems.length };
    });
  }, [saveFavorites]);

  // Remove from favorites
  const removeFavorite = useCallback((productId: number) => {
    setFavorites((prev) => {
      const newItems = prev.items.filter((item) => item.id !== productId);
      saveFavorites(newItems);
      return { items: newItems, count: newItems.length };
    });
  }, [saveFavorites]);

  // Toggle favorite
  const toggleFavorite = useCallback((product: Omit<FavoriteProduct, "addedAt">) => {
    const isFav = favorites.items.some((item) => item.id === product.id);
    if (isFav) {
      removeFavorite(product.id);
    } else {
      addFavorite(product);
    }
  }, [favorites.items, addFavorite, removeFavorite]);

  // Check if product is favorite
  const isFavorite = useCallback((productId: number) => {
    return favorites.items.some((item) => item.id === productId);
  }, [favorites.items]);

  // Clear all favorites
  const clearFavorites = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setFavorites({ items: [], count: 0 });
  }, []);

  return {
    favorites,
    isLoaded,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    clearFavorites,
  };
}

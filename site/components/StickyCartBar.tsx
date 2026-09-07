"use client";

import Link from "next/link";
import { useCart } from "@/hooks/useCart";
import { formatPrice } from "@/lib/utils";
import { usePathname } from "next/navigation";

export default function StickyCartBar() {
  const { cart, isLoaded } = useCart();
  const pathname = usePathname();

  // Don't show on cart page or if cart is empty
  if (!isLoaded || cart.totalItems === 0 || pathname === "/sepet") {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 md:hidden">
      <Link
        href="/sepet"
        className="flex items-center justify-between px-4 py-3 bg-foreground dark:bg-white text-white dark:text-foreground shadow-lg"
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-6 h-6"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
              />
            </svg>
            <span className="absolute -top-2 -right-2 w-5 h-5 bg-accent text-white text-xs font-medium rounded-full flex items-center justify-center">
              {cart.totalItems}
            </span>
          </div>
          <span className="font-medium">Sepeti Gor</span>
        </div>
        <span className="font-semibold">{formatPrice(cart.totalPrice)}</span>
      </Link>
    </div>
  );
}

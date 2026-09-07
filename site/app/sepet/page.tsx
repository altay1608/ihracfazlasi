"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useCart } from "@/hooks/useCart";
import CartItem from "@/components/cart/CartItem";
import WhatsAppOrderButton from "@/components/cart/WhatsAppOrderButton";
import { formatPrice } from "@/lib/utils";

export default function CartPage() {
  const { cart, isLoaded, updateQuantity, removeItem, clearCart } = useCart();

  if (!isLoaded) {
    return (
      <div className="section-sm">
        <div className="container-apple">
          <div className="animate-pulse">
            <div className="h-10 bg-gray-200 rounded w-48 mb-8" />
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-4">
                  <div className="w-24 h-32 bg-gray-200 rounded" />
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                    <div className="h-4 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="section-sm">
      <div className="container-apple">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-display text-foreground">Sepetim</h1>
          {cart.items.length > 0 && (
            <button
              onClick={clearCart}
              className="text-caption text-gray-500 hover:text-red-500 transition-colors"
            >
              Sepeti Temizle
            </button>
          )}
        </div>

        {cart.items.length === 0 ? (
          // Empty State
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
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
                  d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
              </svg>
            </div>
            <h2 className="text-title text-foreground mb-2">Sepetiniz Boş</h2>
            <p className="text-body text-gray-500 mb-8">
              Henüz sepetinize ürün eklemediniz.
            </p>
            <Link href="/urunler" className="btn-primary">
              Alışverişe Başla
            </Link>
          </motion.div>
        ) : (
          // Cart Content
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* Cart Items */}
            <div className="lg:col-span-2">
              <div className="divide-y divide-gray-100">
                {cart.items.map((item, index) => (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <CartItem
                      item={item}
                      onUpdateQuantity={updateQuantity}
                      onRemove={removeItem}
                    />
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1">
              <div className="sticky top-24 bg-gray-100 rounded-apple p-6">
                <h2 className="text-title text-foreground mb-6">Sipariş Özeti</h2>

                <div className="space-y-4 mb-6">
                  <div className="flex justify-between text-body">
                    <span className="text-gray-500">Ürünler ({cart.totalItems} adet)</span>
                    <span className="text-foreground">{formatPrice(cart.totalPrice)}</span>
                  </div>
                  <div className="flex justify-between text-body">
                    <span className="text-gray-500">Kargo</span>
                    <span className="text-success">WhatsApp ile belirlenir</span>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-4 mb-6">
                  <div className="flex justify-between">
                    <span className="text-body font-semibold text-foreground">Toplam</span>
                    <span className="text-title text-foreground">
                      {formatPrice(cart.totalPrice)}
                    </span>
                  </div>
                </div>

                {/* WhatsApp Order Button */}
                <WhatsAppOrderButton items={cart.items} total={cart.totalPrice} />

                {/* Info */}
                <div className="mt-6 p-4 bg-white rounded-apple-sm">
                  <div className="flex gap-3">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                      />
                    </svg>
                    <p className="text-caption text-gray-500">
                      Butona tıkladığınızda WhatsApp açılacak ve siparişiniz hazır mesaj olarak
                      oluşacaktır. Teslimat ve ödeme detaylarını WhatsApp üzerinden
                      konuşabilirsiniz.
                    </p>
                  </div>
                </div>

                {/* Continue Shopping */}
                <Link
                  href="/urunler"
                  className="mt-4 block text-center text-accent hover:underline"
                >
                  Alışverişe Devam Et
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

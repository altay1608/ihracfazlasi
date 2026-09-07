"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface StockNotificationProps {
  productId: number;
  size?: string;
  variantId?: number;
}

export default function StockNotification({ productId, size, variantId }: StockNotificationProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [contact, setContact] = useState("");
  const [contactType, setContactType] = useState<"email" | "phone">("phone");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!contact) {
      setError("Lutfen iletisim bilginizi girin");
      return;
    }

    // Basic validation
    if (contactType === "email" && !contact.includes("@")) {
      setError("Gecerli bir email adresi girin");
      return;
    }

    if (contactType === "phone" && contact.length < 10) {
      setError("Gecerli bir telefon numarasi girin");
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await fetch("/api/v1/stock-notification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          productId,
          variantId,
          size,
          [contactType]: contact,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setIsSuccess(true);
        setTimeout(() => {
          setIsOpen(false);
          setIsSuccess(false);
          setContact("");
        }, 2000);
      } else {
        setError(data.error?.message || "Bir hata olustu");
      }
    } catch {
      setError("Bir hata olustu, lutfen tekrar deneyin");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="w-full py-3 border border-gray-300 dark:border-gray-600 text-foreground dark:text-white rounded-full hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        Stok Gelince Haber Ver
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-x-4 top-1/2 -translate-y-1/2 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 z-50 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 md:max-w-md md:w-full"
            >
              {isSuccess ? (
                <div className="text-center py-4">
                  <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-8 h-8 text-green-600">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-foreground dark:text-white mb-2">Kaydedildi!</h3>
                  <p className="text-gray-500">Stok geldiginde size haber verecegiz.</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-foreground dark:text-white">
                      Stok Bildirimi
                    </h3>
                    <button
                      onClick={() => setIsOpen(false)}
                      className="w-8 h-8 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  <p className="text-sm text-gray-500 mb-4">
                    {size ? `${size} beden stoga geldiginde` : "Bu urun stoga geldiginde"} size haber verelim.
                  </p>

                  <form onSubmit={handleSubmit}>
                    {/* Contact Type Toggle */}
                    <div className="flex gap-2 mb-4">
                      <button
                        type="button"
                        onClick={() => setContactType("phone")}
                        className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                          contactType === "phone"
                            ? "bg-foreground text-white dark:bg-white dark:text-foreground"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                        }`}
                      >
                        Telefon
                      </button>
                      <button
                        type="button"
                        onClick={() => setContactType("email")}
                        className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                          contactType === "email"
                            ? "bg-foreground text-white dark:bg-white dark:text-foreground"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                        }`}
                      >
                        Email
                      </button>
                    </div>

                    {/* Input */}
                    <input
                      type={contactType === "email" ? "email" : "tel"}
                      value={contact}
                      onChange={(e) => setContact(e.target.value)}
                      placeholder={contactType === "email" ? "ornek@email.com" : "05XX XXX XX XX"}
                      className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-800 rounded-xl text-foreground dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent mb-4"
                    />

                    {error && (
                      <p className="text-red-500 text-sm mb-4">{error}</p>
                    )}

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-3 bg-accent text-white font-medium rounded-full hover:bg-accent-hover transition-colors disabled:opacity-50"
                    >
                      {isSubmitting ? "Kaydediliyor..." : "Bana Haber Ver"}
                    </button>
                  </form>
                </>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

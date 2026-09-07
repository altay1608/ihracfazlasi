"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const SIZE_DATA = [
  { size: "S", chest: "92-96", waist: "76-80", hip: "92-96" },
  { size: "M", chest: "96-100", waist: "80-84", hip: "96-100" },
  { size: "L", chest: "100-104", waist: "84-88", hip: "100-104" },
  { size: "XL", chest: "104-108", waist: "88-92", hip: "104-108" },
  { size: "XXL", chest: "108-112", waist: "92-96", hip: "108-112" },
  { size: "3XL", chest: "112-116", waist: "96-100", hip: "112-116" },
  { size: "4XL", chest: "116-120", waist: "100-104", hip: "116-120" },
  { size: "5XL", chest: "120-124", waist: "104-108", hip: "120-124" },
];

interface SizeGuideProps {
  trigger?: React.ReactNode;
}

export default function SizeGuide({ trigger }: SizeGuideProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Trigger */}
      {trigger ? (
        <div onClick={() => setIsOpen(true)}>{trigger}</div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
          </svg>
          Beden Rehberi
        </button>
      )}

      {/* Modal */}
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
              className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 z-50 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden md:max-w-xl md:w-full"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 md:p-6 border-b border-gray-100 dark:border-gray-800">
                <h2 className="text-xl font-semibold text-foreground dark:text-white">
                  Beden Rehberi
                </h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="w-10 h-10 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="p-4 md:p-6 max-h-[70vh] overflow-y-auto">
                {/* How to Measure */}
                <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <h3 className="font-medium text-foreground dark:text-white mb-2">Nasil Olculur?</h3>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <li><strong>Gogus:</strong> En genis yerinizden yatay olarak olcun</li>
                    <li><strong>Bel:</strong> Gobek hizasindan yatay olarak olcun</li>
                    <li><strong>Kalca:</strong> En genis yerinizden yatay olarak olcun</li>
                  </ul>
                </div>

                {/* Size Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="py-3 px-4 text-left font-medium text-foreground dark:text-white">Beden</th>
                        <th className="py-3 px-4 text-center font-medium text-foreground dark:text-white">Gogus (cm)</th>
                        <th className="py-3 px-4 text-center font-medium text-foreground dark:text-white">Bel (cm)</th>
                        <th className="py-3 px-4 text-center font-medium text-foreground dark:text-white">Kalca (cm)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {SIZE_DATA.map((row, idx) => (
                        <tr
                          key={row.size}
                          className={`border-b border-gray-100 dark:border-gray-800 ${
                            idx % 2 === 0 ? "bg-gray-50/50 dark:bg-gray-800/50" : ""
                          }`}
                        >
                          <td className="py-3 px-4 font-medium text-foreground dark:text-white">{row.size}</td>
                          <td className="py-3 px-4 text-center text-gray-600 dark:text-gray-400">{row.chest}</td>
                          <td className="py-3 px-4 text-center text-gray-600 dark:text-gray-400">{row.waist}</td>
                          <td className="py-3 px-4 text-center text-gray-600 dark:text-gray-400">{row.hip}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Note */}
                <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                  * Olculer yaklasik degerlerdir. Markaya gore farklilik gosterebilir.
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

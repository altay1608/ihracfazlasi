"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const FAQ_DATA = [
  {
    category: "Siparis & Satin Alma",
    questions: [
      {
        q: "Nasil siparis verebilirim?",
        a: "Sitemizden begendiginiz urunu secip, beden tercihini yaptiktan sonra sepete ekleyebilirsiniz. Daha sonra WhatsApp uzerinden bizimle iletisime gecerek siparisini tamamlayabilirsiniz. Ayrica magaza ziyaretinizde de alisveris yapabilirsiniz.",
      },
      {
        q: "Odeme yontemleri nelerdir?",
        a: "Nakit ve kredi karti ile odeme yapabilirsiniz. Kapida odeme secenegi de mevcuttur. Taksitli odeme icin kredi kartinizin taksit secenegini kullanabilirsiniz.",
      },
      {
        q: "Fiyatlara KDV dahil mi?",
        a: "Evet, tum fiyatlarimiza KDV dahildir. Ek bir ucret talep edilmez.",
      },
    ],
  },
  {
    category: "Kargo & Teslimat",
    questions: [
      {
        q: "Kargo ucreti ne kadar?",
        a: "500 TL ve uzeri siparislerde kargo ucretsizdir. 500 TL altindaki siparislerde kargo ucreti 50 TL'dir.",
      },
      {
        q: "Kargo ne kadar surede gelir?",
        a: "Siparisleriniz genellikle 1-3 is gunu icinde kargolanir. Kargo suresi bulundugunuz sehire gore 2-4 gun arasinda degisir.",
      },
      {
        q: "Hangi kargo firmasi ile gonderiyorsunuz?",
        a: "Yurtici Kargo ve Aras Kargo ile calisiyoruz. Kargo takip numaraniz WhatsApp uzerinden sizinle paylasilacaktir.",
      },
      {
        q: "Magazadan teslim alabilir miyim?",
        a: "Evet, Inegol magazamizdan siparislerinizi ucretsiz olarak teslim alabilirsiniz.",
      },
    ],
  },
  {
    category: "Iade & Degisim",
    questions: [
      {
        q: "Iade yapabilir miyim?",
        a: "Evet, urunleri 14 gun icinde iade edebilirsiniz. Urunun kullanilmamis, etiketli ve orijinal ambalajinda olmasi gerekmektedir.",
      },
      {
        q: "Beden degisimi yapabilir miyim?",
        a: "Evet, urun elinize ulastiktan sonra 14 gun icinde beden degisimi yapabilirsiniz. Degisim icin WhatsApp uzerinden bizimle iletisime gecin.",
      },
      {
        q: "Iade kargo ucreti kim tarafindan karsilanir?",
        a: "Beden degisimi ve urun hatasi durumlarinda kargo ucreti tarafimizca karsilanir. Diger iade durumlarinda kargo ucreti musteriye aittir.",
      },
    ],
  },
  {
    category: "Urunler",
    questions: [
      {
        q: "Urunler orijinal mi?",
        a: "Evet, tum urunlerimiz orijinal ve ihrac fazlasi urunlerdir. Dunya markalarinin fazla uretimlerinden temin edilmektedir.",
      },
      {
        q: "Ihrac fazlasi ne demek?",
        a: "Ihrac fazlasi urunler, buyuk markalarin yurt disi siparisleri icin uretip, fazla kalan veya kucuk hatalari nedeniyle ihrac edilemeyen urunlerdir. Bu urunler orijinal olup, cok uygun fiyatlarla satisa sunulmaktadir.",
      },
      {
        q: "Beden tablosu var mi?",
        a: "Evet, her urunun detay sayfasinda beden rehberi bulunmaktadir. Olculerinize gore dogru bedeni secebilirsiniz.",
      },
      {
        q: "Stokta olmayan urun icin ne yapmaliyim?",
        a: "Stokta olmayan urunler icin 'Stok Gelince Haber Ver' butonuna tiklayarak bildirim alabilirsiniz. Urun stoga girdiginde size haber verecegiz.",
      },
    ],
  },
  {
    category: "Magaza Bilgileri",
    questions: [
      {
        q: "Magazaniz nerede?",
        a: "Magazamiz Bursa Inegol'de, Ertugulgazi Mahallesi, Kozluca Yolu 13/AA adresinde yer almaktadir.",
      },
      {
        q: "Calisma saatleriniz nedir?",
        a: "Magazamiz her gun 10:00 - 22:00 saatleri arasinda hizmet vermektedir.",
      },
      {
        q: "WhatsApp'tan ulasabilir miyim?",
        a: "Evet, 0538 479 36 96 numarasindan WhatsApp ile 7/24 ulasabilirsiniz.",
      },
    ],
  },
];

function AccordionItem({ question, answer }: { question: string; answer: string }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border-b border-gray-200 dark:border-gray-700">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full py-4 flex items-center justify-between text-left"
      >
        <span className="font-medium text-foreground dark:text-white pr-4">{question}</span>
        <motion.svg
          animate={{ rotate: isOpen ? 180 : 0 }}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
          className="w-5 h-5 flex-shrink-0 text-gray-400"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </motion.svg>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <p className="pb-4 text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
              {answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function SSSPage() {
  const [activeCategory, setActiveCategory] = useState(FAQ_DATA[0].category);

  return (
    <div className="container-wide py-8 md:py-12">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-3xl md:text-4xl font-semibold text-foreground dark:text-white mb-3">
          Sik Sorulan Sorular
        </h1>
        <p className="text-gray-500 max-w-xl mx-auto">
          Merak ettiginiz sorularin cevaplarini buradan bulabilirsiniz. Bulamadiginiz sorular icin WhatsApp'tan bize ulasabilirsiniz.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-8 max-w-4xl mx-auto">
        {/* Category Navigation */}
        <div className="lg:w-64 flex-shrink-0">
          <div className="lg:sticky lg:top-24 flex lg:flex-col gap-2 overflow-x-auto lg:overflow-visible pb-4 lg:pb-0">
            {FAQ_DATA.map((cat) => (
              <button
                key={cat.category}
                onClick={() => setActiveCategory(cat.category)}
                className={`px-4 py-2 rounded-full whitespace-nowrap text-sm font-medium transition-colors ${
                  activeCategory === cat.category
                    ? "bg-foreground dark:bg-white text-white dark:text-foreground"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                {cat.category}
              </button>
            ))}
          </div>
        </div>

        {/* Questions */}
        <div className="flex-1">
          <AnimatePresence mode="wait">
            {FAQ_DATA.filter((cat) => cat.category === activeCategory).map((cat) => (
              <motion.div
                key={cat.category}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <h2 className="text-xl font-semibold text-foreground dark:text-white mb-4">
                  {cat.category}
                </h2>
                <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                  {cat.questions.map((item, idx) => (
                    <AccordionItem key={idx} question={item.q} answer={item.a} />
                  ))}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Contact CTA */}
      <div className="mt-16 text-center">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-2xl p-8 max-w-xl mx-auto">
          <h3 className="text-xl font-semibold text-foreground dark:text-white mb-2">
            Sorunuz mu var?
          </h3>
          <p className="text-gray-500 mb-4">
            Bulamadiginiz cevaplar icin bize WhatsApp'tan ulasabilirsiniz.
          </p>
          <a
            href="https://wa.me/905384793696?text=Merhaba, bir sorum var"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-[#25D366] text-white font-medium rounded-full hover:bg-[#20bd5a] transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
            </svg>
            WhatsApp ile Sor
          </a>
        </div>
      </div>
    </div>
  );
}

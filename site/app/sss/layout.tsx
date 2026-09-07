import { Metadata } from "next";
import { SITE_CONFIG, STORE_INFO } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Sık Sorulan Sorular",
  description: "İhraç Fazlası Giyim hakkında sık sorulan sorular. Sipariş, kargo, iade, ödeme ve ürünler hakkında merak ettikleriniz.",
  keywords: [
    "sık sorulan sorular",
    "SSS",
    "ihraç fazlası",
    "kargo",
    "iade",
    "sipariş",
    "ödeme",
  ],
  alternates: {
    canonical: `${SITE_CONFIG.url}/sss`,
  },
  openGraph: {
    title: "Sık Sorulan Sorular | İhraç Fazlası Giyim",
    description: "Sipariş, kargo, iade ve ürünler hakkında merak ettikleriniz",
    url: `${SITE_CONFIG.url}/sss`,
  },
};

// FAQ structured data for rich snippets
const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Nasıl sipariş verebilirim?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Sitemizden beğendiğiniz ürünü seçip, beden tercihini yaptıktan sonra sepete ekleyebilirsiniz. Daha sonra WhatsApp üzerinden bizimle iletişime geçerek siparişinizi tamamlayabilirsiniz. Ayrıca mağaza ziyaretinizde de alışveriş yapabilirsiniz.",
      },
    },
    {
      "@type": "Question",
      name: "Kargo ücreti ne kadar?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "500 TL ve üzeri siparişlerde kargo ücretsizdir. 500 TL altındaki siparişlerde kargo ücreti 50 TL'dir.",
      },
    },
    {
      "@type": "Question",
      name: "İade yapabilir miyim?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Evet, ürünleri 14 gün içinde iade edebilirsiniz. Ürünün kullanılmamış, etiketli ve orijinal ambalajında olması gerekmektedir.",
      },
    },
    {
      "@type": "Question",
      name: "Ürünler orijinal mi?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Evet, tüm ürünlerimiz orijinal ve ihraç fazlası ürünlerdir. Dünya markalarının fazla üretimlerinden temin edilmektedir.",
      },
    },
    {
      "@type": "Question",
      name: "İhraç fazlası ne demek?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "İhraç fazlası ürünler, büyük markaların yurt dışı siparişleri için üretip, fazla kalan veya küçük hataları nedeniyle ihraç edilemeyen ürünlerdir. Bu ürünler orijinal olup, çok uygun fiyatlarla satışa sunulmaktadır.",
      },
    },
    {
      "@type": "Question",
      name: "Mağazanız nerede?",
      acceptedAnswer: {
        "@type": "Answer",
        text: `Mağazamız ${STORE_INFO.address} adresinde yer almaktadır. Her gün ${STORE_INFO.hours} saatleri arasında hizmet vermektedir.`,
      },
    },
  ],
};

export default function SSSLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      {children}
    </>
  );
}

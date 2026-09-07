import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import Providers from "@/components/Providers";
import ClientWidgets from "@/components/ClientWidgets";
import { SITE_CONFIG, STORE_INFO, BRANDS } from "@/lib/constants";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-inter",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
  interactiveWidget: "resizes-visual",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_CONFIG.url || "https://ihracfazlasigiyim.com"),
  title: {
    default: `${SITE_CONFIG.name} | Dünya Markaları Erkek Giyim - Bursa İnegöl`,
    template: `%s | ${SITE_CONFIG.shortName}`,
  },
  description: SITE_CONFIG.description,
  keywords: [
    "ihraç fazlası",
    "erkek giyim",
    "dünya markaları",
    "Bursa",
    "İnegöl",
    "Prada",
    "Lacoste",
    "Tommy Hilfiger",
    "Hugo Boss",
    "Armani",
    "Calvin Klein",
    "Ralph Lauren",
    "ithal ürün",
    "uygun fiyat",
  ],
  authors: [{ name: SITE_CONFIG.name }],
  creator: SITE_CONFIG.name,
  icons: {
    icon: "/logo.png",
    apple: "/logo.png",
  },
  openGraph: {
    type: "website",
    locale: "tr_TR",
    url: SITE_CONFIG.url,
    siteName: SITE_CONFIG.name,
    title: `${SITE_CONFIG.name} | Dünya Markaları Erkek Giyim`,
    description: SITE_CONFIG.description,
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: SITE_CONFIG.name,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_CONFIG.name} | Dünya Markaları Erkek Giyim`,
    description: SITE_CONFIG.description,
    images: ["/og-image.jpg"],
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: SITE_CONFIG.url,
  },
};

// JSON-LD Schema for LocalBusiness
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "ClothingStore",
  name: STORE_INFO.name,
  description: SITE_CONFIG.description,
  url: SITE_CONFIG.url,
  telephone: STORE_INFO.phoneClean,
  address: {
    "@type": "PostalAddress",
    streetAddress: "Ertuğrulgazi, Kozluca Yolu 13/AA",
    addressLocality: STORE_INFO.city,
    addressRegion: STORE_INFO.region,
    postalCode: STORE_INFO.postalCode,
    addressCountry: "TR",
  },
  geo: {
    "@type": "GeoCoordinates",
    latitude: STORE_INFO.coordinates.lat,
    longitude: STORE_INFO.coordinates.lng,
  },
  openingHoursSpecification: {
    "@type": "OpeningHoursSpecification",
    dayOfWeek: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    opens: "10:00",
    closes: "22:00",
  },
  aggregateRating: {
    "@type": "AggregateRating",
    ratingValue: STORE_INFO.googleRating,
    reviewCount: STORE_INFO.googleReviews,
    bestRating: 5,
    worstRating: 1,
  },
  priceRange: "₺₺",
  image: `${SITE_CONFIG.url}/logo.png`,
  brand: BRANDS.map((brand) => ({
    "@type": "Brand",
    name: brand,
  })),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" className={inter.variable} suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-screen flex flex-col bg-white dark:bg-[#0a0a0a] text-foreground dark:text-white transition-colors">
        <Providers>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
          <ClientWidgets />
        </Providers>
      </body>
    </html>
  );
}

import { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ihracfazlasigiyim.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          "/sepet",
          "/sepet/",
          "/admin/",
          "/favoriler",
          "/favoriler/",
          // Filtreli ve parametre iceren sayfalar
          "/urunler?*",
          // Eski URL formatlari (redirect edilecek ama indexlenmemeli)
          "/*?product*",
          "/*?category*",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}

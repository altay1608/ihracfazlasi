import { MetadataRoute } from "next";
import { SITE_CONFIG } from "@/lib/constants";

const SITE_URL = SITE_CONFIG.url;

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          // Authenticated pages and public filters remain crawlable so Google can read noindex.
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}

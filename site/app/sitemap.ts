import { MetadataRoute } from "next";
import { prisma } from "@/lib/prisma";
import { slugify } from "@/lib/utils";
import { SITE_CONFIG } from "@/lib/constants";

const SITE_URL = SITE_CONFIG.url;
export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Statik sayfalar
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${SITE_URL}/urunler`,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/hakkimizda`,
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${SITE_URL}/sss`,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];

  // Dinamik ürün sayfaları
  let productPages: MetadataRoute.Sitemap = [];
  try {
    const products = await prisma.product.findMany({
      where: { isActive: true },
      select: {
        id: true,
        name: true,
        updatedAt: true,
      },
      orderBy: { updatedAt: "desc" },
    });

    productPages = products.map((product) => ({
      url: `${SITE_URL}/urunler/${slugify(product.name)}-${product.id}`,
      lastModified: product.updatedAt,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    }));
  } catch (error) {
    // Preserve the previous ISR sitemap instead of publishing an incomplete one.
    throw error;
  }

  // Kategori sayfaları
  let categoryPages: MetadataRoute.Sitemap = [];
  try {
    const categories = await prisma.category.findMany({
      where: { isActive: true },
      select: {
        slug: true,
      },
    });

    categoryPages = categories.map((category) => ({
      url: `${SITE_URL}/kategori/${category.slug}`,
      changeFrequency: "weekly" as const,
      priority: 0.7,
    }));
  } catch (error) {
    throw error;
  }

  return [...staticPages, ...productPages, ...categoryPages];
}

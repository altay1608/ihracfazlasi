import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { cache } from "react";
import { categoryIntro, serializeJsonLd } from "@/lib/seo";
import ProductGrid from "@/components/product/ProductGrid";
import { prisma } from "@/lib/prisma";
import { SITE_CONFIG, BRANDS } from "@/lib/constants";
import type { Product, Category } from "@/types";

// ISR: Revalidate every 5 minutes
export const revalidate = 300;

interface PageProps {
  params: Promise<{ slug: string }>;
}

const getCategory = cache(async (slug: string): Promise<Category | null> => {
  try {
    const category = await prisma.category.findUnique({
      where: { slug, isActive: true },
    });
    return category;
  } catch {
    return null;
  }
});

async function getCategoryProducts(categoryId: number): Promise<Product[]> {
  try {
    const products = await prisma.product.findMany({
      where: {
        categoryId,
        isActive: true,
      },
      include: {
        category: true,
        variants: true,
        images: { orderBy: { sortOrder: "asc" } },
      },
      orderBy: { createdAt: "desc" },
    });

    return products.map((p) => ({
      ...p,
      primaryImage:
        p.images.find((img) => img.isPrimary)?.imageUrl || p.images[0]?.imageUrl,
      totalStock: p.variants.reduce((sum, v) => sum + v.stock, 0),
    }));
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const category = await getCategory(slug);

  if (!category) {
    return { title: "Kategori Bulunamadı" };
  }

  const categoryUrl = `${SITE_CONFIG.url}/kategori/${slug}`;
  const description = categoryIntro(slug, category.name).split(". ").slice(0, 2).join(". ");

  return {
    title: `${category.name} | Erkek Giyim`,
    description,
    keywords: [
      category.name,
      "ihraç fazlası",
      "erkek giyim",
      ...BRANDS.slice(0, 5),
      "Bursa",
      "İnegöl",
    ],
    alternates: {
      canonical: categoryUrl,
    },
    openGraph: {
      title: `${category.name} | İhraç Fazlası Giyim`,
      description,
      url: categoryUrl,
    },
  };
}

export default async function CategoryPage({ params }: PageProps) {
  const { slug } = await params;
  const category = await getCategory(slug);

  if (!category) {
    notFound();
  }

  const products = await getCategoryProducts(category.id);
  const breadcrumbs = {
    "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Ana Sayfa", item: SITE_CONFIG.url },
      { "@type": "ListItem", position: 2, name: "Ürünler", item: `${SITE_CONFIG.url}/urunler` },
      { "@type": "ListItem", position: 3, name: category.name, item: `${SITE_CONFIG.url}/kategori/${slug}` },
    ],
  };

  return (
    <div className="section-sm">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(breadcrumbs) }} />
      <div className="container-wide">
        <nav aria-label="Sayfa yolu" className="mb-8 text-gray-500">
          <Link href="/">Ana Sayfa</Link> / <Link href="/urunler">Ürünler</Link> / <span aria-current="page">{category.name}</span>
        </nav>
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="text-display text-foreground mb-4">{category.name}</h1>
          <p className="text-gray-500 max-w-3xl mx-auto mb-4">{categoryIntro(slug, category.name)}</p>
          <p className="text-body-large text-gray-500">
            {products.length} ürün bulundu
          </p>
        </div>

        {/* Products */}
        <ProductGrid products={products} />
      </div>
    </div>
  );
}

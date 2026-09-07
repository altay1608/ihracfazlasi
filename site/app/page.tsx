import dynamic from "next/dynamic";
import Hero from "@/components/home/Hero";
import BrandMarquee from "@/components/home/BrandMarquee";
import Categories from "@/components/home/Categories";
import FeaturedProducts from "@/components/home/FeaturedProducts";
import TrustBadges from "@/components/home/TrustBadges";
import WhatsAppCTA from "@/components/home/WhatsAppCTA";
import { prisma } from "@/lib/prisma";
import type { Product } from "@/types";

// Lazy load heavy components
const PromoVideo = dynamic(() => import("@/components/home/PromoVideo"), {
  loading: () => <div className="h-[60vh] min-h-[400px] max-h-[600px] bg-gray-900 animate-pulse" />,
});

const Testimonials = dynamic(() => import("@/components/home/Testimonials"), {
  loading: () => <div className="h-96 bg-gray-100 animate-pulse" />,
});

// ISR: Revalidate every 60 seconds
export const revalidate = 60;

async function getFeaturedProducts(): Promise<Product[]> {
  try {
    const products = await prisma.product.findMany({
      where: {
        isActive: true,
      },
      include: {
        category: true,
        variants: true,
        images: {
          orderBy: { sortOrder: "asc" },
        },
      },
      orderBy: {
        createdAt: "desc",
      },
      take: 8,
    });

    return products.map((p) => ({
      ...p,
      primaryImage: p.images.find((img) => img.isPrimary)?.imageUrl || p.images[0]?.imageUrl,
      totalStock: p.variants.reduce((sum, v) => sum + v.stock, 0),
    }));
  } catch {
    // Veritabanı henüz kurulmamış olabilir
    return [];
  }
}

export default async function HomePage() {
  const featuredProducts = await getFeaturedProducts();

  return (
    <>
      <Hero />
      <BrandMarquee />
      <TrustBadges />
      <Categories />
      <FeaturedProducts
        products={featuredProducts}
        title="Yeni Eklenen Ürünler"
        subtitle="En son eklenen ürünlerimizi keşfedin"
      />
      <PromoVideo />
      <Testimonials />
      <WhatsAppCTA />
    </>
  );
}

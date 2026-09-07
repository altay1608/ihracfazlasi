import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import ProductGallery from "@/components/product/ProductGallery";
import AddToCartButton from "@/components/product/AddToCartButton";
import FeaturedProducts from "@/components/home/FeaturedProducts";
import { prisma } from "@/lib/prisma";
import { formatPrice, slugify } from "@/lib/utils";
import { WHATSAPP_PHONE, SITE_CONFIG, STORE_INFO } from "@/lib/constants";
import type { Product } from "@/types";

// Lazy load ShareButtons (heavy component with canvas)
const ShareButtons = dynamic(() => import("@/components/share/ShareButtons"), {
  loading: () => <div className="h-32 bg-gray-100 rounded-apple animate-pulse" />,
});

// ISR: Revalidate every 60 seconds
export const revalidate = 60;

interface PageProps {
  params: Promise<{ slug: string }>;
}

function extractIdFromSlug(slug: string): number | null {
  const parts = slug.split("-");
  const lastPart = parts[parts.length - 1];
  const id = parseInt(lastPart);
  return isNaN(id) ? null : id;
}

async function getProduct(slug: string): Promise<Product | null> {
  const id = extractIdFromSlug(slug);
  if (!id) return null;

  try {
    const product = await prisma.product.findUnique({
      where: { id, isActive: true },
      include: {
        category: true,
        variants: true,
        images: { orderBy: { sortOrder: "asc" } },
      },
    });

    if (!product) return null;

    return {
      ...product,
      primaryImage:
        product.images.find((img) => img.isPrimary)?.imageUrl || product.images[0]?.imageUrl,
      totalStock: product.variants.reduce((sum, v) => sum + v.stock, 0),
    };
  } catch {
    return null;
  }
}

async function getRelatedProducts(productId: number, categoryId: number | null): Promise<Product[]> {
  try {
    const products = await prisma.product.findMany({
      where: {
        isActive: true,
        id: { not: productId },
        ...(categoryId && { categoryId }),
      },
      include: {
        category: true,
        variants: true,
        images: { orderBy: { sortOrder: "asc" } },
      },
      take: 4,
    });

    return products.map((p) => ({
      ...p,
      primaryImage: p.images.find((img) => img.isPrimary)?.imageUrl || p.images[0]?.imageUrl,
      totalStock: p.variants.reduce((sum, v) => sum + v.stock, 0),
    }));
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);

  if (!product) {
    return { title: "Ürün Bulunamadı" };
  }

  const productUrl = `${SITE_CONFIG.url}/urunler/${slugify(product.name)}-${product.id}`;
  const description = product.description ||
    `${product.name} - ${formatPrice(product.price)} | İhraç fazlası orijinal ürün. Bursa İnegöl'de mağazamızdan veya online sipariş verin.`;

  return {
    title: `${product.name} | ${formatPrice(product.price)}`,
    description,
    keywords: [
      product.name,
      product.sku,
      product.category?.name || "giyim",
      "ihraç fazlası",
      "erkek giyim",
      "Bursa",
      "İnegöl",
    ],
    openGraph: {
      title: product.name,
      description,
      url: productUrl,
      images: product.primaryImage ? [{
        url: product.primaryImage,
        width: 800,
        height: 800,
        alt: product.name,
      }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: product.name,
      description,
      images: product.primaryImage ? [product.primaryImage] : undefined,
    },
    alternates: {
      canonical: productUrl,
    },
  };
}

export default async function ProductDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const product = await getProduct(slug);

  if (!product) {
    notFound();
  }

  const relatedProducts = await getRelatedProducts(product.id, product.categoryId);

  // WhatsApp message for this product
  const whatsappMessage = `Merhaba! "${product.name}" (${product.sku}) ürünü hakkında bilgi almak istiyorum.`;
  const whatsappLink = `https://wa.me/${WHATSAPP_PHONE}?text=${encodeURIComponent(whatsappMessage)}`;

  // Product Schema JSON-LD
  const productUrl = `${SITE_CONFIG.url}/urunler/${slugify(product.name)}-${product.id}`;
  const productSchema = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    description: product.description || `${product.name} - İhraç fazlası orijinal ürün`,
    image: product.images?.map(img => img.imageUrl) || [],
    sku: product.sku,
    brand: {
      "@type": "Brand",
      name: product.name.split(" ")[0], // First word is usually brand
    },
    offers: {
      "@type": "Offer",
      url: productUrl,
      priceCurrency: "TRY",
      price: product.price,
      availability: (product.totalStock ?? 0) > 0
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      seller: {
        "@type": "Organization",
        name: STORE_INFO.name,
      },
    },
    category: product.category?.name || "Giyim",
  };

  // BreadcrumbList Schema JSON-LD
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Ana Sayfa",
        item: SITE_CONFIG.url,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Ürünler",
        item: `${SITE_CONFIG.url}/urunler`,
      },
      ...(product.category ? [{
        "@type": "ListItem",
        position: 3,
        name: product.category.name,
        item: `${SITE_CONFIG.url}/kategori/${product.category.slug}`,
      }] : []),
      {
        "@type": "ListItem",
        position: product.category ? 4 : 3,
        name: product.name,
        item: productUrl,
      },
    ],
  };

  return (
    <>
      {/* Product Schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productSchema) }}
      />
      {/* Breadcrumb Schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />

      <div className="section-sm">
        <div className="container-wide">
          {/* Breadcrumb */}
          <nav className="mb-8">
            <ol className="flex items-center gap-2 text-caption text-gray-500">
              <li>
                <Link href="/" className="hover:text-foreground transition-colors">
                  Ana Sayfa
                </Link>
              </li>
              <li>/</li>
              <li>
                <Link href="/urunler" className="hover:text-foreground transition-colors">
                  Ürünler
                </Link>
              </li>
              {product.category && (
                <>
                  <li>/</li>
                  <li>
                    <Link
                      href={`/kategori/${product.category.slug}`}
                      className="hover:text-foreground transition-colors"
                    >
                      {product.category.name}
                    </Link>
                  </li>
                </>
              )}
              <li>/</li>
              <li className="text-foreground">{product.name}</li>
            </ol>
          </nav>

          {/* Product Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16">
            {/* Gallery */}
            <div>
              <ProductGallery images={product.images || []} productName={product.name} />
            </div>

            {/* Product Info */}
            <div className="lg:sticky lg:top-24 lg:self-start">
              {/* Category */}
              {product.category && (
                <Link
                  href={`/kategori/${product.category.slug}`}
                  className="text-caption text-accent hover:underline"
                >
                  {product.category.name}
                </Link>
              )}

              {/* Name */}
              <h1 className="text-headline text-foreground mt-2 mb-4">{product.name}</h1>

              {/* SKU */}
              <p className="text-caption text-gray-500 mb-4">SKU: {product.sku}</p>

              {/* Price */}
              <p className="text-display text-foreground mb-6">{formatPrice(product.price)}</p>

              {/* Description */}
              {product.description && (
                <div className="prose prose-gray mb-8">
                  <p className="text-body text-gray-500">{product.description}</p>
                </div>
              )}

              {/* Add to Cart Section */}
              <div className="bg-gray-100 rounded-apple p-6 mb-6">
                <AddToCartButton product={product} />
              </div>

              {/* WhatsApp Contact */}
              <a
                href={whatsappLink}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full py-4 border border-success text-success rounded-full hover:bg-success hover:text-white transition-all"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                Bu Urun Hakkinda Bilgi Al
              </a>

              {/* Social Share */}
              <div className="mt-4">
                <ShareButtons
                  product={{
                    name: product.name,
                    price: product.price,
                    sku: product.sku,
                    primaryImage: product.primaryImage,
                  }}
                  productUrl={`/urunler/${slug}`}
                />
              </div>

              {/* Features */}
              <div className="mt-8 pt-8 border-t border-gray-200">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-5 h-5 text-gray-500"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"
                        />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">Kargo</p>
                      <p className="text-caption text-gray-500">Hızlı Teslimat</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-5 h-5 text-gray-500"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">Kalite</p>
                      <p className="text-caption text-gray-500">İhraç Fazlası</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Related Products */}
      {relatedProducts.length > 0 && (
        <FeaturedProducts
          products={relatedProducts}
          title="Benzer Ürünler"
          subtitle="Beğenebileceğiniz diğer ürünler"
          showViewAll={false}
        />
      )}
    </>
  );
}

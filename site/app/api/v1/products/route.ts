import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse, paginatedResponse } from "@/lib/api-auth";
import { slugify } from "@/lib/utils";
import { z } from "zod";

// Brand SKU prefix mapping
const BRAND_SKU_MAP: Record<string, string> = {
  "Prada": "PRD",
  "Lacoste": "LCST",
  "Tommy Hilfiger": "TH",
  "Hugo Boss": "HB",
  "Armani": "ARM",
  "Versace": "VRS",
  "Calvin Klein": "CK",
  "Ralph Lauren": "RL",
  "Gucci": "GC",
  "Burberry": "BRB",
};

// GET /api/v1/products - Ürün listesi
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const search = searchParams.get("search") || searchParams.get("q") || "";
    const categoryId = searchParams.get("category_id");
    const categorySlug = searchParams.get("kategori");
    const isActive = searchParams.get("is_active");
    const page = parseInt(searchParams.get("page") || searchParams.get("sayfa") || "1");
    const limit = Math.min(parseInt(searchParams.get("limit") || "50"), 100);
    const skip = (page - 1) * limit;

    // Price filters
    const minPrice = searchParams.get("minFiyat");
    const maxPrice = searchParams.get("maxFiyat");

    // Brand filter (comma-separated)
    const brands = searchParams.get("marka")?.split(",").filter(Boolean) || [];

    // Size filter (comma-separated)
    const sizes = searchParams.get("beden")?.split(",").filter(Boolean) || [];

    // Sort
    const sort = searchParams.get("siralama") || "newest";

    // Build where clause
    const where: Record<string, unknown> = {};

    if (search) {
      where.OR = [
        { name: { contains: search } },
        { sku: { contains: search.toUpperCase() } },
        { description: { contains: search } },
      ];
    }

    if (categoryId) {
      where.categoryId = parseInt(categoryId);
    }

    // Category by slug
    if (categorySlug) {
      const category = await prisma.category.findUnique({
        where: { slug: categorySlug },
      });
      if (category) {
        where.categoryId = category.id;
      }
    }

    if (isActive !== null && isActive !== undefined) {
      where.isActive = isActive === "true";
    } else {
      where.isActive = true; // Default to active only
    }

    // Price range filter
    if (minPrice || maxPrice) {
      where.price = {};
      if (minPrice) {
        (where.price as Record<string, number>).gte = parseFloat(minPrice);
      }
      if (maxPrice) {
        (where.price as Record<string, number>).lte = parseFloat(maxPrice);
      }
    }

    // Brand filter (by SKU prefix)
    if (brands.length > 0) {
      const skuPrefixes = brands
        .map((brand) => BRAND_SKU_MAP[brand])
        .filter(Boolean);
      if (skuPrefixes.length > 0) {
        where.OR = skuPrefixes.map((prefix) => ({
          sku: { startsWith: prefix },
        }));
      }
    }

    // Size filter - products that have variants with these sizes in stock
    let sizeFilter = {};
    if (sizes.length > 0) {
      sizeFilter = {
        variants: {
          some: {
            size: { in: sizes },
            stock: { gt: 0 },
          },
        },
      };
    }

    // Combine where clauses
    const finalWhere = sizes.length > 0 ? { ...where, ...sizeFilter } : where;

    // Sort order
    let orderBy: Record<string, string> = { createdAt: "desc" };
    switch (sort) {
      case "price-asc":
      case "fiyat-artan":
        orderBy = { price: "asc" };
        break;
      case "price-desc":
      case "fiyat-azalan":
        orderBy = { price: "desc" };
        break;
      case "name-asc":
        orderBy = { name: "asc" };
        break;
      case "name-desc":
        orderBy = { name: "desc" };
        break;
      default:
        orderBy = { createdAt: "desc" };
    }

    const [products, totalItems] = await Promise.all([
      prisma.product.findMany({
        where: finalWhere,
        include: {
          category: true,
          variants: true,
          images: { orderBy: { sortOrder: "asc" } },
        },
        orderBy,
        skip,
        take: limit,
      }),
      prisma.product.count({ where: finalWhere }),
    ]);

    const formattedProducts = products.map((p) => ({
      id: p.id,
      sku: p.sku,
      name: p.name,
      price: p.price,
      costPrice: p.costPrice,
      category: p.category
        ? { id: p.category.id, name: p.category.name }
        : null,
      primaryImage:
        p.images.find((img) => img.isPrimary)?.imageUrl || p.images[0]?.imageUrl || null,
      totalStock: p.variants.reduce((sum, v) => sum + v.stock, 0),
      variants: p.variants.map((v) => ({
        id: v.id,
        size: v.size,
        color: v.color,
        stock: v.stock,
      })),
    }));

    return paginatedResponse(formattedProducts, page, limit, totalItems);
  } catch (error) {
    console.error("Products GET error:", error);
    return errorResponse("SERVER_ERROR", "Ürünler alınamadı", undefined, 500);
  }
}

// POST /api/v1/products - Yeni ürün ekle
const createProductSchema = z.object({
  sku: z.string().min(1, "SKU zorunlu"),
  name: z.string().min(1, "Ürün adı zorunlu"),
  description: z.string().optional(),
  price: z.number().positive("Fiyat pozitif olmalı"),
  costPrice: z.number().positive().optional(),
  categoryId: z.number().optional(),
  variants: z
    .array(
      z.object({
        size: z.string().optional(),
        color: z.string().optional(),
        stock: z.number().int().min(0).default(0),
        barcode: z.string().optional(),
      })
    )
    .optional(),
});

export async function POST(request: NextRequest) {
  // Auth check
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const validation = createProductSchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const data = validation.data;

    // Check if SKU already exists
    const existingProduct = await prisma.product.findUnique({
      where: { sku: data.sku },
    });

    if (existingProduct) {
      return errorResponse("SKU_EXISTS", "Bu SKU zaten kullanılıyor", data.sku, 409);
    }

    // If categoryId provided, verify it exists
    if (data.categoryId) {
      const category = await prisma.category.findUnique({
        where: { id: data.categoryId },
      });
      if (!category) {
        return errorResponse("CATEGORY_NOT_FOUND", "Kategori bulunamadı", undefined, 404);
      }
    }

    // Create product with variants
    const product = await prisma.product.create({
      data: {
        sku: data.sku,
        name: data.name,
        description: data.description,
        price: data.price,
        costPrice: data.costPrice,
        categoryId: data.categoryId,
        variants: data.variants
          ? {
              create: data.variants.map((v) => ({
                size: v.size || null,
                color: v.color || null,
                stock: v.stock,
                barcode: v.barcode || null,
              })),
            }
          : undefined,
      },
      include: {
        variants: true,
      },
    });

    return successResponse(
      {
        id: product.id,
        sku: product.sku,
        message: "Ürün başarıyla eklendi",
      },
      201
    );
  } catch (error) {
    console.error("Products POST error:", error);
    return errorResponse("SERVER_ERROR", "Ürün eklenemedi", undefined, 500);
  }
}

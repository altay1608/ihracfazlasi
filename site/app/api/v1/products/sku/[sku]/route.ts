import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

interface RouteContext {
  params: Promise<{ sku: string }>;
}

// GET /api/v1/products/sku/[sku] - SKU ile ürün sorgula
export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { sku } = await context.params;

    const product = await prisma.product.findUnique({
      where: { sku },
      include: {
        category: true,
        variants: true,
        images: { orderBy: { sortOrder: "asc" } },
      },
    });

    if (!product) {
      return errorResponse(
        "PRODUCT_NOT_FOUND",
        "Ürün bulunamadı",
        `SKU: ${sku} sistemde kayıtlı değil`,
        404
      );
    }

    return successResponse({
      id: product.id,
      sku: product.sku,
      name: product.name,
      description: product.description,
      price: product.price,
      costPrice: product.costPrice,
      category: product.category
        ? { id: product.category.id, name: product.category.name }
        : null,
      images: product.images.map((img) => ({
        id: img.id,
        url: img.imageUrl,
        isPrimary: img.isPrimary,
      })),
      variants: product.variants.map((v) => ({
        id: v.id,
        size: v.size,
        color: v.color,
        stock: v.stock,
      })),
      totalStock: product.variants.reduce((sum, v) => sum + v.stock, 0),
      isActive: product.isActive,
      createdAt: product.createdAt.toISOString(),
    });
  } catch (error) {
    console.error("Product by SKU GET error:", error);
    return errorResponse("SERVER_ERROR", "Ürün alınamadı", undefined, 500);
  }
}

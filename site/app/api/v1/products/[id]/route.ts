import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { z } from "zod";

interface RouteContext {
  params: Promise<{ id: string }>;
}

// GET /api/v1/products/[id] - Ürün detayı
export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const productId = parseInt(id);

    if (isNaN(productId)) {
      return errorResponse("INVALID_ID", "Geçersiz ürün ID", undefined, 400);
    }

    const product = await prisma.product.findUnique({
      where: { id: productId },
      include: {
        category: true,
        variants: true,
        images: { orderBy: { sortOrder: "asc" } },
      },
    });

    if (!product) {
      return errorResponse("PRODUCT_NOT_FOUND", "Ürün bulunamadı", undefined, 404);
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
    console.error("Product GET error:", error);
    return errorResponse("SERVER_ERROR", "Ürün alınamadı", undefined, 500);
  }
}

// PUT /api/v1/products/[id] - Ürün güncelle
const updateProductSchema = z.object({
  name: z.string().min(1).optional(),
  description: z.string().optional(),
  price: z.number().positive().optional(),
  costPrice: z.number().positive().nullable().optional(),
  categoryId: z.number().nullable().optional(),
  isActive: z.boolean().optional(),
});

export async function PUT(request: NextRequest, context: RouteContext) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const { id } = await context.params;
    const productId = parseInt(id);

    if (isNaN(productId)) {
      return errorResponse("INVALID_ID", "Geçersiz ürün ID", undefined, 400);
    }

    const body = await request.json();
    const validation = updateProductSchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const data = validation.data;

    // Check if product exists
    const existingProduct = await prisma.product.findUnique({
      where: { id: productId },
    });

    if (!existingProduct) {
      return errorResponse("PRODUCT_NOT_FOUND", "Ürün bulunamadı", undefined, 404);
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

    // Update product
    await prisma.product.update({
      where: { id: productId },
      data: {
        ...(data.name && { name: data.name }),
        ...(data.description !== undefined && { description: data.description }),
        ...(data.price && { price: data.price }),
        ...(data.costPrice !== undefined && { costPrice: data.costPrice }),
        ...(data.categoryId !== undefined && { categoryId: data.categoryId }),
        ...(data.isActive !== undefined && { isActive: data.isActive }),
      },
    });

    return successResponse({ message: "Ürün güncellendi" });
  } catch (error) {
    console.error("Product PUT error:", error);
    return errorResponse("SERVER_ERROR", "Ürün güncellenemedi", undefined, 500);
  }
}

// DELETE /api/v1/products/[id] - Ürün sil (pasife al)
export async function DELETE(request: NextRequest, context: RouteContext) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const { id } = await context.params;
    const productId = parseInt(id);

    if (isNaN(productId)) {
      return errorResponse("INVALID_ID", "Geçersiz ürün ID", undefined, 400);
    }

    const product = await prisma.product.findUnique({
      where: { id: productId },
    });

    if (!product) {
      return errorResponse("PRODUCT_NOT_FOUND", "Ürün bulunamadı", undefined, 404);
    }

    // Soft delete - just mark as inactive
    await prisma.product.update({
      where: { id: productId },
      data: { isActive: false },
    });

    return successResponse({ message: "Ürün pasife alındı" });
  } catch (error) {
    console.error("Product DELETE error:", error);
    return errorResponse("SERVER_ERROR", "Ürün silinemedi", undefined, 500);
  }
}

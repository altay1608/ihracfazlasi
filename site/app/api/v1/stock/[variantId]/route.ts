import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

interface RouteContext {
  params: Promise<{ variantId: string }>;
}

// GET /api/v1/stock/[variantId] - Variant ID ile stok sorgula
export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { variantId } = await context.params;
    const id = parseInt(variantId);

    if (isNaN(id)) {
      return errorResponse("INVALID_ID", "Geçersiz variant ID", undefined, 400);
    }

    const variant = await prisma.productVariant.findUnique({
      where: { id },
      include: {
        product: true,
      },
    });

    if (!variant) {
      return errorResponse("VARIANT_NOT_FOUND", "Variant bulunamadı", undefined, 404);
    }

    return successResponse({
      variantId: variant.id,
      productSku: variant.product.sku,
      productName: variant.product.name,
      size: variant.size,
      color: variant.color,
      stock: variant.stock,
    });
  } catch (error) {
    console.error("Stock GET error:", error);
    return errorResponse("SERVER_ERROR", "Stok alınamadı", undefined, 500);
  }
}

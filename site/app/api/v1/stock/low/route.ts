import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";
import { LOW_STOCK_THRESHOLD } from "@/lib/constants";

// GET /api/v1/stock/low?threshold=3 - Düşük stok listesi
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const threshold = parseInt(searchParams.get("threshold") || String(LOW_STOCK_THRESHOLD));

    const lowStockVariants = await prisma.productVariant.findMany({
      where: {
        stock: { lte: threshold },
        product: { isActive: true },
      },
      include: {
        product: true,
      },
      orderBy: { stock: "asc" },
    });

    const formattedVariants = lowStockVariants.map((v) => ({
      variantId: v.id,
      sku: v.product.sku,
      productName: v.product.name,
      size: v.size,
      color: v.color,
      stock: v.stock,
    }));

    return successResponse({
      data: formattedVariants,
      count: formattedVariants.length,
      threshold,
    });
  } catch (error) {
    console.error("Low stock GET error:", error);
    return errorResponse("SERVER_ERROR", "Düşük stok listesi alınamadı", undefined, 500);
  }
}

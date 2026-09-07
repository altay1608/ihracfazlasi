import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

// GET /api/v1/stock/query?sku=XXX&size=M&color=Kırmızı
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sku = searchParams.get("sku");
    const size = searchParams.get("size");
    const color = searchParams.get("color");

    if (!sku) {
      return errorResponse("MISSING_SKU", "SKU parametresi zorunlu", undefined, 400);
    }

    // Find product by SKU
    const product = await prisma.product.findUnique({
      where: { sku },
      include: {
        variants: true,
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

    // Find matching variant
    let variant = product.variants.find(
      (v) =>
        (size === null || v.size === size) &&
        (color === null || v.color === color)
    );

    // If only one variant exists and no specific size/color requested, return it
    if (!variant && product.variants.length === 1 && !size && !color) {
      variant = product.variants[0];
    }

    if (!variant) {
      return errorResponse(
        "VARIANT_NOT_FOUND",
        "Belirtilen beden/renk kombinasyonu bulunamadı",
        `SKU: ${sku}, Beden: ${size || "belirtilmedi"}, Renk: ${color || "belirtilmedi"}`,
        404
      );
    }

    return successResponse({
      variantId: variant.id,
      productSku: product.sku,
      productName: product.name,
      size: variant.size,
      color: variant.color,
      stock: variant.stock,
    });
  } catch (error) {
    console.error("Stock query error:", error);
    return errorResponse("SERVER_ERROR", "Stok sorgulanamadı", undefined, 500);
  }
}

import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { z } from "zod";

const stockUpdateBySkuSchema = z.object({
  sku: z.string().min(1, "SKU zorunlu"),
  size: z.string().optional(),
  color: z.string().optional(),
  change: z.number().int(),
  reason: z.enum(["sale", "restock", "adjustment", "return"]),
  note: z.string().optional(),
});

// POST /api/v1/stock/update-by-sku - SKU ile stok güncelle
export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const validation = stockUpdateBySkuSchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const { sku, size, color, change, reason, note } = validation.data;

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
        (size === undefined || v.size === size) &&
        (color === undefined || v.color === color)
    );

    // If only one variant exists and no specific size/color requested, use it
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

    const previousStock = variant.stock;
    const newStock = previousStock + change;

    // Don't allow negative stock
    if (newStock < 0) {
      return errorResponse(
        "INSUFFICIENT_STOCK",
        "Yetersiz stok",
        `Mevcut: ${previousStock}, İstenen değişim: ${change}`,
        409
      );
    }

    // Update stock and create log in transaction
    await prisma.$transaction([
      prisma.productVariant.update({
        where: { id: variant.id },
        data: { stock: newStock },
      }),
      prisma.stockLog.create({
        data: {
          variantId: variant.id,
          changeType: reason,
          quantityChange: change,
          previousStock,
          newStock,
          note,
        },
      }),
    ]);

    return successResponse({
      variantId: variant.id,
      previousStock,
      newStock,
      message: "Stok güncellendi",
    });
  } catch (error) {
    console.error("Stock update by SKU error:", error);
    return errorResponse("SERVER_ERROR", "Stok güncellenemedi", undefined, 500);
  }
}

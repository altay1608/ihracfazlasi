import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { z } from "zod";

const stockUpdateSchema = z.object({
  variant_id: z.number().int().positive(),
  change: z.number().int(), // Positive to add, negative to subtract
  reason: z.enum(["sale", "restock", "adjustment", "return"]),
  note: z.string().optional(),
});

// POST /api/v1/stock/update - Stok güncelle (variant ID ile)
export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const validation = stockUpdateSchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const { variant_id, change, reason, note } = validation.data;

    // Get current variant
    const variant = await prisma.productVariant.findUnique({
      where: { id: variant_id },
    });

    if (!variant) {
      return errorResponse("VARIANT_NOT_FOUND", "Variant bulunamadı", undefined, 404);
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
        where: { id: variant_id },
        data: { stock: newStock },
      }),
      prisma.stockLog.create({
        data: {
          variantId: variant_id,
          changeType: reason,
          quantityChange: change,
          previousStock,
          newStock,
          note,
        },
      }),
    ]);

    return successResponse({
      variantId: variant_id,
      previousStock,
      newStock,
      message: "Stok güncellendi",
    });
  } catch (error) {
    console.error("Stock update error:", error);
    return errorResponse("SERVER_ERROR", "Stok güncellenemedi", undefined, 500);
  }
}

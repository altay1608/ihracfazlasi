import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { z } from "zod";

interface RouteContext {
  params: Promise<{ id: string }>;
}

const cancelSaleSchema = z.object({
  reason: z.string().optional(),
  restore_stock: z.boolean().default(true),
});

// POST /api/v1/sales/[id]/cancel - Satış iptal
export async function POST(request: NextRequest, context: RouteContext) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const { id } = await context.params;
    const saleId = parseInt(id);

    if (isNaN(saleId)) {
      return errorResponse("INVALID_ID", "Geçersiz satış ID", undefined, 400);
    }

    const body = await request.json();
    const validation = cancelSaleSchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const { reason, restore_stock } = validation.data;

    // Get sale with items
    const sale = await prisma.sale.findUnique({
      where: { id: saleId },
      include: {
        items: {
          include: {
            variant: true,
          },
        },
      },
    });

    if (!sale) {
      return errorResponse("SALE_NOT_FOUND", "Satış bulunamadı", undefined, 404);
    }

    // Cancel sale and restore stock if requested
    await prisma.$transaction(async (tx) => {
      // Delete sale (cascade deletes items)
      await tx.sale.delete({
        where: { id: saleId },
      });

      // Restore stock if requested
      if (restore_stock) {
        for (const item of sale.items) {
          if (item.variantId) {
            const variant = await tx.productVariant.findUnique({
              where: { id: item.variantId },
            });

            if (variant) {
              const previousStock = variant.stock;
              const newStock = previousStock + item.quantity;

              await tx.productVariant.update({
                where: { id: item.variantId },
                data: { stock: newStock },
              });

              await tx.stockLog.create({
                data: {
                  variantId: item.variantId,
                  changeType: "return",
                  quantityChange: item.quantity,
                  previousStock,
                  newStock,
                  note: `Satış #${saleId} iptali${reason ? `: ${reason}` : ""}`,
                },
              });
            }
          }
        }
      }
    });

    return successResponse({
      message: restore_stock
        ? "Satış iptal edildi, stok geri eklendi"
        : "Satış iptal edildi",
    });
  } catch (error) {
    console.error("Sale cancel error:", error);
    return errorResponse("SERVER_ERROR", "Satış iptal edilemedi", undefined, 500);
  }
}

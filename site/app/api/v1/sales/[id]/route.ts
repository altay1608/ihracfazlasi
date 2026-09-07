import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

interface RouteContext {
  params: Promise<{ id: string }>;
}

// GET /api/v1/sales/[id] - Satış detayı
export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { id } = await context.params;
    const saleId = parseInt(id);

    if (isNaN(saleId)) {
      return errorResponse("INVALID_ID", "Geçersiz satış ID", undefined, 400);
    }

    const sale = await prisma.sale.findUnique({
      where: { id: saleId },
      include: {
        items: {
          include: {
            variant: {
              include: {
                product: true,
              },
            },
          },
        },
      },
    });

    if (!sale) {
      return errorResponse("SALE_NOT_FOUND", "Satış bulunamadı", undefined, 404);
    }

    return successResponse({
      id: sale.id,
      date: sale.saleDate.toISOString(),
      totalAmount: sale.totalAmount,
      paymentMethod: sale.paymentMethod,
      notes: sale.notes,
      source: sale.source,
      items: sale.items.map((item) => ({
        productName: item.productName,
        sku: item.variant?.product.sku,
        size: item.size,
        color: item.color,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        subtotal: item.quantity * item.unitPrice,
      })),
    });
  } catch (error) {
    console.error("Sale GET error:", error);
    return errorResponse("SERVER_ERROR", "Satış alınamadı", undefined, 500);
  }
}

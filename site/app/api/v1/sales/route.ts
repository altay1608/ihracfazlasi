import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse, paginatedResponse } from "@/lib/api-auth";
import { z } from "zod";

// GET /api/v1/sales - Satış listesi
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get("page") || "1");
    const limit = Math.min(parseInt(searchParams.get("limit") || "20"), 100);
    const skip = (page - 1) * limit;

    const [sales, totalItems] = await Promise.all([
      prisma.sale.findMany({
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
        orderBy: { saleDate: "desc" },
        skip,
        take: limit,
      }),
      prisma.sale.count(),
    ]);

    const formattedSales = sales.map((sale) => ({
      id: sale.id,
      date: sale.saleDate.toISOString(),
      totalAmount: sale.totalAmount,
      paymentMethod: sale.paymentMethod,
      source: sale.source,
      items: sale.items.map((item) => ({
        productName: item.productName,
        size: item.size,
        color: item.color,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
      })),
    }));

    return paginatedResponse(formattedSales, page, limit, totalItems);
  } catch (error) {
    console.error("Sales GET error:", error);
    return errorResponse("SERVER_ERROR", "Satışlar alınamadı", undefined, 500);
  }
}

// POST /api/v1/sales - Yeni satış kaydet
const createSaleSchema = z.object({
  payment_method: z.enum(["cash", "card"]).optional(),
  items: z.array(
    z.object({
      sku: z.string().min(1),
      size: z.string().optional(),
      color: z.string().optional(),
      quantity: z.number().int().positive(),
      unit_price: z.number().positive(),
    })
  ).min(1, "En az bir ürün gerekli"),
  notes: z.string().optional(),
});

export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const validation = createSaleSchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const { payment_method, items, notes } = validation.data;

    // Validate all items and find variants
    const itemsWithVariants = await Promise.all(
      items.map(async (item) => {
        const product = await prisma.product.findUnique({
          where: { sku: item.sku },
          include: { variants: true },
        });

        if (!product) {
          throw new Error(`Ürün bulunamadı: ${item.sku}`);
        }

        // Find matching variant
        let variant = product.variants.find(
          (v) =>
            (item.size === undefined || v.size === item.size) &&
            (item.color === undefined || v.color === item.color)
        );

        // If only one variant and no size/color specified, use it
        if (!variant && product.variants.length === 1 && !item.size && !item.color) {
          variant = product.variants[0];
        }

        if (!variant) {
          throw new Error(`Variant bulunamadı: ${item.sku} - Beden: ${item.size}, Renk: ${item.color}`);
        }

        if (variant.stock < item.quantity) {
          throw new Error(
            `Yetersiz stok: ${item.sku} - Mevcut: ${variant.stock}, İstenen: ${item.quantity}`
          );
        }

        return {
          ...item,
          variant,
          product,
        };
      })
    );

    // Calculate total
    const totalAmount = itemsWithVariants.reduce(
      (sum, item) => sum + item.unit_price * item.quantity,
      0
    );

    // Create sale with transaction
    const sale = await prisma.$transaction(async (tx) => {
      // Create sale
      const newSale = await tx.sale.create({
        data: {
          totalAmount,
          paymentMethod: payment_method,
          notes,
          source: "telegram",
          items: {
            create: itemsWithVariants.map((item) => ({
              variantId: item.variant.id,
              productName: item.product.name,
              size: item.variant.size,
              color: item.variant.color,
              quantity: item.quantity,
              unitPrice: item.unit_price,
            })),
          },
        },
        include: { items: true },
      });

      // Update stock and create logs for each item
      for (const item of itemsWithVariants) {
        const previousStock = item.variant.stock;
        const newStock = previousStock - item.quantity;

        await tx.productVariant.update({
          where: { id: item.variant.id },
          data: { stock: newStock },
        });

        await tx.stockLog.create({
          data: {
            variantId: item.variant.id,
            changeType: "sale",
            quantityChange: -item.quantity,
            previousStock,
            newStock,
            note: `Satış #${newSale.id}`,
          },
        });
      }

      return newSale;
    });

    return successResponse(
      {
        saleId: sale.id,
        totalAmount: sale.totalAmount,
        itemsCount: sale.items.length,
        stockUpdated: true,
        message: "Satış kaydedildi",
      },
      201
    );
  } catch (error) {
    console.error("Sales POST error:", error);
    if (error instanceof Error) {
      return errorResponse("SALE_ERROR", error.message, undefined, 400);
    }
    return errorResponse("SERVER_ERROR", "Satış kaydedilemedi", undefined, 500);
  }
}

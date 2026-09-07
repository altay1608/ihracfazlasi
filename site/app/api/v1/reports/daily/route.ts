import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

// GET /api/v1/reports/daily?date=2026-01-27
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const dateStr = searchParams.get("date") || new Date().toISOString().split("T")[0];

    const startDate = new Date(dateStr);
    startDate.setHours(0, 0, 0, 0);

    const endDate = new Date(dateStr);
    endDate.setHours(23, 59, 59, 999);

    // Get sales for the day
    const sales = await prisma.sale.findMany({
      where: {
        saleDate: {
          gte: startDate,
          lte: endDate,
        },
      },
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
      orderBy: { saleDate: "asc" },
    });

    // Calculate summary
    const totalSales = sales.length;
    const totalRevenue = sales.reduce((sum, sale) => sum + sale.totalAmount, 0);
    const totalItemsSold = sales.reduce(
      (sum, sale) => sum + sale.items.reduce((itemSum, item) => itemSum + item.quantity, 0),
      0
    );

    // Calculate profit (if cost prices are available)
    let totalProfit = 0;
    sales.forEach((sale) => {
      sale.items.forEach((item) => {
        const costPrice = item.variant?.product.costPrice || 0;
        totalProfit += (item.unitPrice - costPrice) * item.quantity;
      });
    });

    // Payment breakdown
    const paymentBreakdown = {
      cash: sales
        .filter((s) => s.paymentMethod === "cash")
        .reduce((sum, s) => sum + s.totalAmount, 0),
      card: sales
        .filter((s) => s.paymentMethod === "card")
        .reduce((sum, s) => sum + s.totalAmount, 0),
    };

    // Top products
    const productSales: Record<
      string,
      { sku: string; name: string; quantity: number; revenue: number }
    > = {};

    sales.forEach((sale) => {
      sale.items.forEach((item) => {
        const sku = item.variant?.product.sku || "unknown";
        const name = item.productName;
        const key = sku;

        if (!productSales[key]) {
          productSales[key] = { sku, name, quantity: 0, revenue: 0 };
        }
        productSales[key].quantity += item.quantity;
        productSales[key].revenue += item.unitPrice * item.quantity;
      });
    });

    const topProducts = Object.values(productSales)
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10)
      .map((p) => ({
        sku: p.sku,
        name: p.name,
        quantitySold: p.quantity,
        revenue: p.revenue,
      }));

    // Sales list
    const salesList = sales.map((sale) => ({
      id: sale.id,
      time: sale.saleDate.toLocaleTimeString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      amount: sale.totalAmount,
      items: sale.items.reduce((sum, item) => sum + item.quantity, 0),
    }));

    return successResponse({
      date: dateStr,
      summary: {
        totalSales,
        totalRevenue,
        totalProfit,
        totalItemsSold,
      },
      paymentBreakdown,
      topProducts,
      sales: salesList,
    });
  } catch (error) {
    console.error("Daily report error:", error);
    return errorResponse("SERVER_ERROR", "Rapor oluşturulamadı", undefined, 500);
  }
}

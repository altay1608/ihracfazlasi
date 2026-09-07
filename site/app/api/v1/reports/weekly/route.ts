import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

// GET /api/v1/reports/weekly?start_date=2026-01-20
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const startDateStr = searchParams.get("start_date");

    let startDate: Date;
    if (startDateStr) {
      startDate = new Date(startDateStr);
    } else {
      // Default to start of current week (Monday)
      startDate = new Date();
      const day = startDate.getDay();
      const diff = startDate.getDate() - day + (day === 0 ? -6 : 1);
      startDate.setDate(diff);
    }
    startDate.setHours(0, 0, 0, 0);

    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 6);
    endDate.setHours(23, 59, 59, 999);

    // Get sales for the week
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

    // Calculate profit
    let totalProfit = 0;
    sales.forEach((sale) => {
      sale.items.forEach((item) => {
        const costPrice = item.variant?.product.costPrice || 0;
        totalProfit += (item.unitPrice - costPrice) * item.quantity;
      });
    });

    const averageDaily = totalRevenue / 7;

    // Daily breakdown
    const dailyBreakdown: { date: string; revenue: number; sales: number }[] = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startDate);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split("T")[0];

      const daySales = sales.filter((s) => {
        const saleDate = new Date(s.saleDate).toISOString().split("T")[0];
        return saleDate === dateStr;
      });

      dailyBreakdown.push({
        date: dateStr,
        revenue: daySales.reduce((sum, s) => sum + s.totalAmount, 0),
        sales: daySales.length,
      });
    }

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

    // Format period string
    const periodStart = startDate.toLocaleDateString("tr-TR", {
      day: "numeric",
    });
    const periodEnd = endDate.toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });

    return successResponse({
      period: `${periodStart}-${periodEnd}`,
      summary: {
        totalSales,
        totalRevenue,
        totalProfit,
        averageDaily,
      },
      dailyBreakdown,
      topProducts,
    });
  } catch (error) {
    console.error("Weekly report error:", error);
    return errorResponse("SERVER_ERROR", "Rapor oluşturulamadı", undefined, 500);
  }
}

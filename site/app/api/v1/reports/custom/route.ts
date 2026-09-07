import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

// GET /api/v1/reports/custom?start=2026-01-01&end=2026-01-27
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const startDateStr = searchParams.get("start");
    const endDateStr = searchParams.get("end");

    if (!startDateStr || !endDateStr) {
      return errorResponse(
        "MISSING_PARAMS",
        "Başlangıç ve bitiş tarihi zorunlu",
        "start ve end parametrelerini YYYY-MM-DD formatında girin"
      );
    }

    const startDate = new Date(startDateStr);
    startDate.setHours(0, 0, 0, 0);

    const endDate = new Date(endDateStr);
    endDate.setHours(23, 59, 59, 999);

    if (startDate > endDate) {
      return errorResponse(
        "INVALID_DATE_RANGE",
        "Başlangıç tarihi bitiş tarihinden sonra olamaz"
      );
    }

    // Calculate days in range
    const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;

    // Get sales for the period
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
                product: {
                  include: {
                    category: true,
                  },
                },
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

    const averageDaily = totalRevenue / daysDiff;
    const averageOrder = totalSales > 0 ? totalRevenue / totalSales : 0;

    // Daily breakdown
    const dailyBreakdown: { date: string; revenue: number; sales: number }[] = [];
    const currentDate = new Date(startDate);

    while (currentDate <= endDate) {
      const dateStr = currentDate.toISOString().split("T")[0];
      const daySales = sales.filter((s) => {
        const saleDate = s.saleDate.toISOString().split("T")[0];
        return saleDate === dateStr;
      });

      dailyBreakdown.push({
        date: dateStr,
        revenue: daySales.reduce((sum, s) => sum + s.totalAmount, 0),
        sales: daySales.length,
      });

      currentDate.setDate(currentDate.getDate() + 1);
    }

    // Category breakdown
    const categorySales: Record<string, { name: string; revenue: number }> = {};
    sales.forEach((sale) => {
      sale.items.forEach((item) => {
        const categoryName = item.variant?.product.category?.name || "Kategorisiz";
        if (!categorySales[categoryName]) {
          categorySales[categoryName] = { name: categoryName, revenue: 0 };
        }
        categorySales[categoryName].revenue += item.unitPrice * item.quantity;
      });
    });

    const categoryBreakdown = Object.values(categorySales)
      .sort((a, b) => b.revenue - a.revenue)
      .map((c) => ({
        category: c.name,
        revenue: c.revenue,
        percent: totalRevenue > 0 ? (c.revenue / totalRevenue) * 100 : 0,
      }));

    // Top products
    const productSales: Record<
      string,
      { sku: string; name: string; quantity: number; revenue: number }
    > = {};

    sales.forEach((sale) => {
      sale.items.forEach((item) => {
        const sku = item.variant?.product.sku || "unknown";
        const name = item.productName;

        if (!productSales[sku]) {
          productSales[sku] = { sku, name, quantity: 0, revenue: 0 };
        }
        productSales[sku].quantity += item.quantity;
        productSales[sku].revenue += item.unitPrice * item.quantity;
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

    // Payment breakdown
    const paymentBreakdown = {
      cash: sales
        .filter((s) => s.paymentMethod === "cash")
        .reduce((sum, s) => sum + s.totalAmount, 0),
      card: sales
        .filter((s) => s.paymentMethod === "card")
        .reduce((sum, s) => sum + s.totalAmount, 0),
    };

    // Format period
    const formatDate = (d: Date) =>
      d.toLocaleDateString("tr-TR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    const period = `${formatDate(startDate)} - ${formatDate(endDate)}`;

    return successResponse({
      period,
      days: daysDiff,
      summary: {
        totalSales,
        totalRevenue,
        totalProfit,
        totalItemsSold,
        averageDaily,
        averageOrder,
      },
      dailyBreakdown,
      categoryBreakdown,
      topProducts,
      paymentBreakdown,
    });
  } catch (error) {
    console.error("Custom report error:", error);
    return errorResponse("SERVER_ERROR", "Rapor oluşturulamadı", undefined, 500);
  }
}

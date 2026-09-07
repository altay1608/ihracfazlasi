import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { successResponse, errorResponse } from "@/lib/api-auth";

// GET /api/v1/reports/monthly?year=2026&month=1
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const now = new Date();
    const year = parseInt(searchParams.get("year") || String(now.getFullYear()));
    const month = parseInt(searchParams.get("month") || String(now.getMonth() + 1));

    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0, 23, 59, 59, 999);
    const daysInMonth = endDate.getDate();

    // Get sales for the month
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

    // Get previous month sales for comparison
    const prevStartDate = new Date(year, month - 2, 1);
    const prevEndDate = new Date(year, month - 1, 0, 23, 59, 59, 999);

    const prevMonthSales = await prisma.sale.findMany({
      where: {
        saleDate: {
          gte: prevStartDate,
          lte: prevEndDate,
        },
      },
    });

    const previousMonthRevenue = prevMonthSales.reduce((sum, s) => sum + s.totalAmount, 0);

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

    const averageDaily = totalRevenue / daysInMonth;
    const averageOrder = totalSales > 0 ? totalRevenue / totalSales : 0;

    // Comparison
    const changeAmount = totalRevenue - previousMonthRevenue;
    const changePercent =
      previousMonthRevenue > 0 ? (changeAmount / previousMonthRevenue) * 100 : 0;

    // Daily breakdown for best/worst day
    const dailySales: Record<string, { revenue: number; count: number }> = {};
    sales.forEach((sale) => {
      const dateStr = sale.saleDate.toISOString().split("T")[0];
      if (!dailySales[dateStr]) {
        dailySales[dateStr] = { revenue: 0, count: 0 };
      }
      dailySales[dateStr].revenue += sale.totalAmount;
      dailySales[dateStr].count += 1;
    });

    const sortedDays = Object.entries(dailySales).sort((a, b) => b[1].revenue - a[1].revenue);
    const bestDay = sortedDays[0] ? { date: sortedDays[0][0], revenue: sortedDays[0][1].revenue } : null;
    const worstDay =
      sortedDays.length > 0
        ? { date: sortedDays[sortedDays.length - 1][0], revenue: sortedDays[sortedDays.length - 1][1].revenue }
        : null;

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

    // Format period string
    const monthNames = [
      "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
      "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    ];
    const period = `${monthNames[month - 1]} ${year}`;

    return successResponse({
      period,
      summary: {
        totalSales,
        totalRevenue,
        totalProfit,
        totalItemsSold,
        averageDaily,
        averageOrder,
      },
      comparison: previousMonthRevenue > 0
        ? {
            previousMonthRevenue,
            changeAmount,
            changePercent,
          }
        : null,
      bestDay,
      worstDay,
      categoryBreakdown,
      topProducts,
      paymentBreakdown,
    });
  } catch (error) {
    console.error("Monthly report error:", error);
    return errorResponse("SERVER_ERROR", "Rapor oluşturulamadı", undefined, 500);
  }
}

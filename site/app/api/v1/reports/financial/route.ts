import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey } from "@/lib/api-auth";

// GET /api/v1/reports/financial - Finansal rapor
export async function GET(request: NextRequest) {
  const authResult = await validateApiKey(request);
  if (!authResult.success) return authResult.error;

  try {
    const { searchParams } = new URL(request.url);
    const period = searchParams.get("period") || "month"; // day, week, month, year
    const dateParam = searchParams.get("date");

    // Tarih aralığını hesapla
    const now = dateParam ? new Date(dateParam) : new Date();
    let startDate: Date;
    let endDate: Date;
    let periodLabel: string;

    switch (period) {
      case "day":
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
        periodLabel = startDate.toISOString().split("T")[0];
        break;
      case "week":
        const dayOfWeek = now.getDay();
        const diffToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - diffToMonday);
        endDate = new Date(startDate.getTime() + 6 * 24 * 60 * 60 * 1000);
        endDate.setHours(23, 59, 59);
        periodLabel = `${startDate.toISOString().split("T")[0]} - ${endDate.toISOString().split("T")[0]}`;
        break;
      case "year":
        startDate = new Date(now.getFullYear(), 0, 1);
        endDate = new Date(now.getFullYear(), 11, 31, 23, 59, 59);
        periodLabel = `${now.getFullYear()}`;
        break;
      case "month":
      default:
        startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59);
        periodLabel = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    }

    // Satışları al
    const sales = await prisma.sale.findMany({
      where: {
        saleDate: {
          gte: startDate,
          lte: endDate,
        },
      },
      include: {
        items: true,
      },
    });

    // Satış özeti
    const totalRevenue = sales.reduce((sum, s) => sum + s.totalAmount, 0);
    const totalSales = sales.length;
    const totalItemsSold = sales.reduce(
      (sum, s) => sum + s.items.reduce((isum, item) => isum + item.quantity, 0),
      0
    );

    // Maliyet hesapla (ürünlerin costPrice'ı üzerinden)
    let totalCost = 0;
    for (const sale of sales) {
      for (const item of sale.items) {
        if (item.variantId) {
          const variant = await prisma.productVariant.findUnique({
            where: { id: item.variantId },
            include: { product: true },
          });
          if (variant?.product?.costPrice) {
            totalCost += variant.product.costPrice * item.quantity;
          }
        }
      }
    }

    // Brüt kar
    const grossProfit = totalRevenue - totalCost;
    const grossMargin = totalRevenue > 0 ? (grossProfit / totalRevenue) * 100 : 0;

    // Giderleri al
    const expenses = await prisma.expense.findMany({
      where: {
        expenseDate: {
          gte: startDate,
          lte: endDate,
        },
      },
    });

    const totalExpenses = expenses.reduce((sum, e) => sum + e.amount, 0);

    // Gider kategorileri
    const expensesByCategory: Record<string, number> = {};
    for (const expense of expenses) {
      expensesByCategory[expense.category] =
        (expensesByCategory[expense.category] || 0) + expense.amount;
    }

    // Net kar
    const netProfit = grossProfit - totalExpenses;
    const netMargin = totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0;

    return NextResponse.json({
      success: true,
      data: {
        period: periodLabel,
        periodType: period,
        dateRange: {
          start: startDate.toISOString(),
          end: endDate.toISOString(),
        },
        revenue: {
          total: totalRevenue,
          salesCount: totalSales,
          itemsSold: totalItemsSold,
          averageOrder: totalSales > 0 ? totalRevenue / totalSales : 0,
        },
        costs: {
          productCost: totalCost,
          expenses: totalExpenses,
          total: totalCost + totalExpenses,
        },
        profit: {
          gross: grossProfit,
          grossMargin: Math.round(grossMargin * 100) / 100,
          net: netProfit,
          netMargin: Math.round(netMargin * 100) / 100,
        },
        expenseBreakdown: expensesByCategory,
        summary: {
          isProfit: netProfit >= 0,
          status: netProfit >= 0 ? "kar" : "zarar",
        },
      },
    });
  } catch (error) {
    console.error("Financial report error:", error);
    return NextResponse.json(
      {
        success: false,
        error: { code: "REPORT_ERROR", message: "Finansal rapor oluşturulamadı" },
      },
      { status: 500 }
    );
  }
}

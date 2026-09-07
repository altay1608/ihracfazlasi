import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey } from "@/lib/api-auth";

// POST - Kasa kapat ve rapor oluştur
export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const { closingAmount } = body;

    const today = new Date().toISOString().split("T")[0];

    // Get today's cash register
    const cashRegister = await prisma.cashRegister.findUnique({
      where: { date: today },
    });

    if (!cashRegister) {
      return NextResponse.json(
        { success: false, error: { message: "Bugün kasa açılmamış. Önce /kasaac komutunu kullanın." } },
        { status: 400 }
      );
    }

    if (cashRegister.closedAt) {
      return NextResponse.json(
        { success: false, error: { message: "Bugün kasa zaten kapatılmış" } },
        { status: 400 }
      );
    }

    // Get today's sales (cash only)
    const todayStart = new Date(today);
    todayStart.setHours(0, 0, 0, 0);
    const todayEnd = new Date(today);
    todayEnd.setHours(23, 59, 59, 999);

    const sales = await prisma.sale.findMany({
      where: {
        saleDate: {
          gte: todayStart,
          lte: todayEnd,
        },
      },
    });

    const cashSales = sales
      .filter((s) => s.paymentMethod === "cash" || s.paymentMethod === "nakit")
      .reduce((sum, s) => sum + s.totalAmount, 0);

    const cardSales = sales
      .filter((s) => s.paymentMethod === "card" || s.paymentMethod === "kart")
      .reduce((sum, s) => sum + s.totalAmount, 0);

    const totalSales = sales.reduce((sum, s) => sum + s.totalAmount, 0);

    // Get today's expenses
    const expenses = await prisma.expense.findMany({
      where: {
        expenseDate: {
          gte: todayStart,
          lte: todayEnd,
        },
      },
    });

    const totalExpenses = expenses.reduce((sum, e) => sum + e.amount, 0);

    // Calculate expected closing
    const expectedAmount = cashRegister.openingAmount + cashSales - totalExpenses;
    const difference = closingAmount !== undefined ? closingAmount - expectedAmount : null;

    // Update cash register
    const updated = await prisma.cashRegister.update({
      where: { date: today },
      data: {
        closingAmount: closingAmount ?? expectedAmount,
        expectedAmount,
        difference,
        closedAt: new Date(),
      },
    });

    return NextResponse.json({
      success: true,
      data: {
        cashRegister: updated,
        report: {
          openingAmount: cashRegister.openingAmount,
          cashSales,
          cardSales,
          totalSales,
          totalExpenses,
          expectedClosing: expectedAmount,
          actualClosing: closingAmount ?? expectedAmount,
          difference: difference ?? 0,
          salesCount: sales.length,
          expenseCount: expenses.length,
        },
      },
    });
  } catch (error) {
    console.error("Cash register close error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Kasa kapatılamadı" } },
      { status: 500 }
    );
  }
}

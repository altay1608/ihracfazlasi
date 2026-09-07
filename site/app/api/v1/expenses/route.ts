import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey } from "@/lib/api-auth";

const EXPENSE_CATEGORIES = ["kira", "fatura", "maas", "mal_alimi", "diger"];

// GET /api/v1/expenses - Gider listele
export async function GET(request: NextRequest) {
  const authResult = await validateApiKey(request);
  if (!authResult.success) return authResult.error;

  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "50");
    const category = searchParams.get("category");
    const startDate = searchParams.get("startDate");
    const endDate = searchParams.get("endDate");

    const where: Record<string, unknown> = {};

    if (category && EXPENSE_CATEGORIES.includes(category)) {
      where.category = category;
    }

    if (startDate || endDate) {
      where.expenseDate = {};
      if (startDate) {
        (where.expenseDate as Record<string, unknown>).gte = new Date(startDate);
      }
      if (endDate) {
        (where.expenseDate as Record<string, unknown>).lte = new Date(endDate);
      }
    }

    const expenses = await prisma.expense.findMany({
      where,
      orderBy: { expenseDate: "desc" },
      take: limit,
    });

    // Toplam hesapla
    const total = expenses.reduce((sum, e) => sum + e.amount, 0);

    return NextResponse.json({
      success: true,
      data: expenses,
      summary: {
        count: expenses.length,
        total,
      },
    });
  } catch (error) {
    console.error("Get expenses error:", error);
    return NextResponse.json(
      {
        success: false,
        error: { code: "FETCH_ERROR", message: "Giderler alınamadı" },
      },
      { status: 500 }
    );
  }
}

// POST /api/v1/expenses - Gider ekle
export async function POST(request: NextRequest) {
  const authResult = await validateApiKey(request);
  if (!authResult.success) return authResult.error;

  try {
    const body = await request.json();
    const { amount, category, description, expenseDate } = body;

    // Validasyon
    if (!amount || typeof amount !== "number" || amount <= 0) {
      return NextResponse.json(
        {
          success: false,
          error: { code: "INVALID_AMOUNT", message: "Geçerli bir tutar girin" },
        },
        { status: 400 }
      );
    }

    if (!category || !EXPENSE_CATEGORIES.includes(category)) {
      return NextResponse.json(
        {
          success: false,
          error: {
            code: "INVALID_CATEGORY",
            message: `Geçerli kategoriler: ${EXPENSE_CATEGORIES.join(", ")}`,
          },
        },
        { status: 400 }
      );
    }

    const expense = await prisma.expense.create({
      data: {
        amount,
        category,
        description: description || null,
        expenseDate: expenseDate ? new Date(expenseDate) : new Date(),
      },
    });

    return NextResponse.json({
      success: true,
      data: expense,
    });
  } catch (error) {
    console.error("Create expense error:", error);
    return NextResponse.json(
      {
        success: false,
        error: { code: "CREATE_ERROR", message: "Gider eklenemedi" },
      },
      { status: 500 }
    );
  }
}

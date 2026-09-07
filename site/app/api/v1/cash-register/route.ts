import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey } from "@/lib/api-auth";

// GET - Bugünün kasa durumu veya belirli tarih
export async function GET(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  const { searchParams } = new URL(request.url);
  const date = searchParams.get("date") || new Date().toISOString().split("T")[0];

  try {
    const cashRegister = await prisma.cashRegister.findUnique({
      where: { date },
    });

    return NextResponse.json({
      success: true,
      data: cashRegister,
    });
  } catch (error) {
    console.error("Cash register fetch error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Kasa bilgisi alınamadı" } },
      { status: 500 }
    );
  }
}

// POST - Kasa aç
export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const { openingAmount, notes } = body;

    if (typeof openingAmount !== "number" || openingAmount < 0) {
      return NextResponse.json(
        { success: false, error: { message: "Geçersiz açılış tutarı" } },
        { status: 400 }
      );
    }

    const today = new Date().toISOString().split("T")[0];

    // Check if already opened
    const existing = await prisma.cashRegister.findUnique({
      where: { date: today },
    });

    if (existing) {
      return NextResponse.json(
        { success: false, error: { message: "Bugün kasa zaten açılmış" } },
        { status: 400 }
      );
    }

    const cashRegister = await prisma.cashRegister.create({
      data: {
        date: today,
        openingAmount,
        notes,
      },
    });

    return NextResponse.json({
      success: true,
      data: cashRegister,
    });
  } catch (error) {
    console.error("Cash register open error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Kasa açılamadı" } },
      { status: 500 }
    );
  }
}

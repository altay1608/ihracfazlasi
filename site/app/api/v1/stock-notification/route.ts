import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// POST - Create stock notification
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { productId, variantId, size, email, phone } = body;

    if (!productId) {
      return NextResponse.json(
        { success: false, error: { message: "Urun ID gerekli" } },
        { status: 400 }
      );
    }

    if (!email && !phone) {
      return NextResponse.json(
        { success: false, error: { message: "Email veya telefon gerekli" } },
        { status: 400 }
      );
    }

    // Check if product exists
    const product = await prisma.product.findUnique({
      where: { id: productId },
    });

    if (!product) {
      return NextResponse.json(
        { success: false, error: { message: "Urun bulunamadi" } },
        { status: 404 }
      );
    }

    // Check if notification already exists
    const existing = await prisma.stockNotification.findFirst({
      where: {
        productId,
        size: size || null,
        OR: [
          { email: email || undefined },
          { phone: phone || undefined },
        ],
        notified: false,
      },
    });

    if (existing) {
      return NextResponse.json({
        success: true,
        data: { message: "Zaten bildirim listenizdesiniz" },
      });
    }

    // Create notification
    const notification = await prisma.stockNotification.create({
      data: {
        productId,
        variantId: variantId || null,
        size: size || null,
        email: email || null,
        phone: phone || null,
      },
    });

    return NextResponse.json({
      success: true,
      data: {
        id: notification.id,
        message: "Stok geldiginde size haber verecegiz!",
      },
    });
  } catch (error) {
    console.error("Stock notification error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Bildirim kaydedilemedi" } },
      { status: 500 }
    );
  }
}

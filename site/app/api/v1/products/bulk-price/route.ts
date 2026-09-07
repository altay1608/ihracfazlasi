import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey } from "@/lib/api-auth";

// POST - Toplu fiyat güncelleme
export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const { percentage, skuPrefix, categorySlug, action } = body;

    if (typeof percentage !== "number" || percentage <= 0 || percentage > 100) {
      return NextResponse.json(
        { success: false, error: { message: "Geçersiz yüzde değeri (1-100 arası olmalı)" } },
        { status: 400 }
      );
    }

    if (action !== "increase" && action !== "decrease") {
      return NextResponse.json(
        { success: false, error: { message: "Geçersiz işlem (increase veya decrease olmalı)" } },
        { status: 400 }
      );
    }

    // Build query
    const where: Record<string, unknown> = { isActive: true };

    if (skuPrefix) {
      where.sku = { startsWith: skuPrefix.toUpperCase() };
    }

    if (categorySlug) {
      const category = await prisma.category.findUnique({
        where: { slug: categorySlug },
      });
      if (category) {
        where.categoryId = category.id;
      }
    }

    // Get products to update
    const products = await prisma.product.findMany({
      where,
      select: { id: true, name: true, price: true, sku: true },
    });

    if (products.length === 0) {
      return NextResponse.json(
        { success: false, error: { message: "Kriterlere uyan ürün bulunamadı" } },
        { status: 404 }
      );
    }

    // Calculate new prices
    const multiplier = action === "increase"
      ? 1 + (percentage / 100)
      : 1 - (percentage / 100);

    const updates = products.map((p) => ({
      id: p.id,
      sku: p.sku,
      name: p.name,
      oldPrice: p.price,
      newPrice: Math.round(p.price * multiplier),
    }));

    // Return preview (actual update happens on confirm)
    return NextResponse.json({
      success: true,
      data: {
        count: products.length,
        action,
        percentage,
        filter: {
          skuPrefix: skuPrefix || null,
          categorySlug: categorySlug || null,
        },
        preview: updates.slice(0, 10), // First 10 for preview
        totalOldValue: products.reduce((sum, p) => sum + p.price, 0),
        totalNewValue: updates.reduce((sum, u) => sum + u.newPrice, 0),
      },
    });
  } catch (error) {
    console.error("Bulk price preview error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Fiyat önizleme hatası" } },
      { status: 500 }
    );
  }
}

// PUT - Toplu fiyat güncellemeyi onayla
export async function PUT(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const { percentage, skuPrefix, categorySlug, action } = body;

    if (typeof percentage !== "number" || percentage <= 0 || percentage > 100) {
      return NextResponse.json(
        { success: false, error: { message: "Geçersiz yüzde değeri" } },
        { status: 400 }
      );
    }

    // Build query
    const where: Record<string, unknown> = { isActive: true };

    if (skuPrefix) {
      where.sku = { startsWith: skuPrefix.toUpperCase() };
    }

    if (categorySlug) {
      const category = await prisma.category.findUnique({
        where: { slug: categorySlug },
      });
      if (category) {
        where.categoryId = category.id;
      }
    }

    // Get and update products
    const products = await prisma.product.findMany({ where });

    const multiplier = action === "increase"
      ? 1 + (percentage / 100)
      : 1 - (percentage / 100);

    let updatedCount = 0;
    for (const product of products) {
      const newPrice = Math.round(product.price * multiplier);
      await prisma.product.update({
        where: { id: product.id },
        data: { price: newPrice },
      });
      updatedCount++;
    }

    return NextResponse.json({
      success: true,
      data: {
        updatedCount,
        action,
        percentage,
      },
    });
  } catch (error) {
    console.error("Bulk price update error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Toplu fiyat güncelleme hatası" } },
      { status: 500 }
    );
  }
}

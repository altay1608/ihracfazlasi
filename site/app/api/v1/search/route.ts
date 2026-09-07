import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// GET - Search products
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q") || "";
  const limit = parseInt(searchParams.get("limit") || "10");

  if (!query || query.length < 2) {
    return NextResponse.json({ success: true, data: [] });
  }

  try {
    const products = await prisma.product.findMany({
      where: {
        isActive: true,
        OR: [
          { name: { contains: query } },
          { sku: { contains: query.toUpperCase() } },
          { description: { contains: query } },
        ],
      },
      select: {
        id: true,
        name: true,
        sku: true,
        price: true,
        images: {
          where: { isPrimary: true },
          select: { imageUrl: true },
          take: 1,
        },
        category: {
          select: { name: true, slug: true },
        },
      },
      take: limit,
      orderBy: { createdAt: "desc" },
    });

    const results = products.map((p) => ({
      id: p.id,
      name: p.name,
      sku: p.sku,
      price: p.price,
      image: p.images[0]?.imageUrl || null,
      category: p.category?.name || null,
      categorySlug: p.category?.slug || null,
    }));

    return NextResponse.json({ success: true, data: results });
  } catch (error) {
    console.error("Search error:", error);
    return NextResponse.json(
      { success: false, error: { message: "Arama hatasi" } },
      { status: 500 }
    );
  }
}

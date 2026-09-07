import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { validateAdminSession, ADMIN_COOKIE_NAME } from '@/lib/admin-auth';

export async function GET(request: NextRequest) {
  const sessionCookie = request.cookies.get(ADMIN_COOKIE_NAME)?.value;
  if (!(await validateAdminSession(sessionCookie || ''))) {
    return NextResponse.json({ success: false, message: 'Yetkisiz' }, { status: 401 });
  }

  try {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const [totalProducts, totalSales, todaySales, lowStockVariants, totalCategories, recentSales] =
      await Promise.all([
        prisma.product.count({ where: { isActive: true } }),
        prisma.sale.count(),
        prisma.sale.findMany({
          where: { saleDate: { gte: today, lt: tomorrow } },
          include: { items: true },
        }),
        prisma.productVariant.findMany({
          where: { stock: { lte: 3 } },
          include: { product: { select: { name: true, sku: true } } },
          orderBy: { stock: 'asc' },
          take: 10,
        }),
        prisma.category.count(),
        prisma.sale.findMany({
          orderBy: { saleDate: 'desc' },
          take: 5,
          include: { items: true },
        }),
      ]);

    const todayRevenue = todaySales.reduce((sum, s) => sum + s.totalAmount, 0);
    const todayItemsSold = todaySales.reduce(
      (sum, s) => sum + s.items.reduce((is, i) => is + i.quantity, 0),
      0
    );

    return NextResponse.json({
      success: true,
      data: {
        totalProducts,
        totalSales,
        totalCategories,
        today: {
          sales: todaySales.length,
          revenue: todayRevenue,
          itemsSold: todayItemsSold,
        },
        lowStock: lowStockVariants.map((v) => ({
          id: v.id,
          productName: v.product.name,
          sku: v.product.sku,
          size: v.size,
          color: v.color,
          stock: v.stock,
        })),
        recentSales: recentSales.map((s) => ({
          id: s.id,
          date: s.saleDate.toISOString(),
          total: s.totalAmount,
          items: s.items.reduce((sum, i) => sum + i.quantity, 0),
          paymentMethod: s.paymentMethod,
        })),
      },
    });
  } catch (error) {
    console.error('Dashboard error:', error);
    return NextResponse.json({ success: false, message: 'Sunucu hatası' }, { status: 500 });
  }
}

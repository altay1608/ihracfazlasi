import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { validateAdminSession, ADMIN_COOKIE_NAME } from '@/lib/admin-auth';

async function checkAuth(request: NextRequest) {
  const cookie = request.cookies.get(ADMIN_COOKIE_NAME)?.value;
  return validateAdminSession(cookie || '');
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  const { id } = await params;
  const product = await prisma.product.findUnique({
    where: { id: parseInt(id) },
    include: { category: true, variants: true, images: true },
  });

  if (!product) {
    return NextResponse.json({ success: false, message: 'Ürün bulunamadı' }, { status: 404 });
  }
  return NextResponse.json({ success: true, data: product });
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  try {
    const { id } = await params;
    const productId = parseInt(id);
    const body = await request.json();
    const { name, sku, description, categoryId, price, costPrice, isActive, imageUrl } = body;

    const product = await prisma.product.update({
      where: { id: productId },
      data: {
        name: name.trim(),
        sku: sku.trim().toUpperCase(),
        description: description?.trim() || null,
        categoryId: categoryId ? parseInt(categoryId) : null,
        price: parseFloat(price),
        costPrice: costPrice ? parseFloat(costPrice) : null,
        isActive: isActive !== false,
      },
    });

    // If a new imageUrl provided, replace the primary image
    if (imageUrl !== undefined) {
      if (imageUrl) {
        await prisma.productImage.deleteMany({ where: { productId, isPrimary: true } });
        await prisma.productImage.create({
          data: { productId, imageUrl, isPrimary: true, sortOrder: 0 },
        });
      } else {
        // imageUrl === '' means remove the primary image
        await prisma.productImage.deleteMany({ where: { productId, isPrimary: true } });
      }
    }

    const updated = await prisma.product.findUnique({
      where: { id: productId },
      include: { images: { orderBy: { sortOrder: 'asc' }, take: 1 } },
    });

    return NextResponse.json({ success: true, data: updated });
  } catch (error) {
    console.error('Product update error:', error);
    return NextResponse.json({ success: false, message: 'Ürün güncellenemedi' }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  try {
    const { id } = await params;
    await prisma.product.delete({ where: { id: parseInt(id) } });
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Product delete error:', error);
    return NextResponse.json({ success: false, message: 'Ürün silinemedi' }, { status: 500 });
  }
}

import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { slugify } from "@/lib/utils";
import { z } from "zod";

// GET /api/v1/categories - Kategori listesi
export async function GET() {
  try {
    const categories = await prisma.category.findMany({
      where: { isActive: true },
      include: {
        _count: {
          select: {
            products: {
              where: { isActive: true },
            },
          },
        },
      },
      orderBy: { name: "asc" },
    });

    const formattedCategories = categories.map((c) => ({
      id: c.id,
      name: c.name,
      slug: c.slug,
      productCount: c._count.products,
    }));

    return successResponse(formattedCategories);
  } catch (error) {
    console.error("Categories GET error:", error);
    return errorResponse("SERVER_ERROR", "Kategoriler alınamadı", undefined, 500);
  }
}

// POST /api/v1/categories - Yeni kategori ekle
const createCategorySchema = z.object({
  name: z.string().min(1, "Kategori adı zorunlu"),
  parentId: z.number().optional(),
});

export async function POST(request: NextRequest) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const body = await request.json();
    const validation = createCategorySchema.safeParse(body);

    if (!validation.success) {
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => e.message).join(", ")
      );
    }

    const { name, parentId } = validation.data;
    const slug = slugify(name);

    // Check if slug already exists
    const existingCategory = await prisma.category.findUnique({
      where: { slug },
    });

    if (existingCategory) {
      return errorResponse("CATEGORY_EXISTS", "Bu isimde bir kategori zaten var", undefined, 409);
    }

    // If parentId provided, verify it exists
    if (parentId) {
      const parent = await prisma.category.findUnique({
        where: { id: parentId },
      });
      if (!parent) {
        return errorResponse("PARENT_NOT_FOUND", "Üst kategori bulunamadı", undefined, 404);
      }
    }

    const category = await prisma.category.create({
      data: {
        name,
        slug,
        parentId,
      },
    });

    return successResponse(
      {
        id: category.id,
        name: category.name,
        slug: category.slug,
      },
      201
    );
  } catch (error) {
    console.error("Categories POST error:", error);
    return errorResponse("SERVER_ERROR", "Kategori eklenemedi", undefined, 500);
  }
}

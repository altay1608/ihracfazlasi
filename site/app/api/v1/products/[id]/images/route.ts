import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { uploadImage } from "@/lib/cloudinary";

interface RouteContext {
  params: Promise<{ id: string }>;
}

// POST /api/v1/products/[id]/images - Görsel yükle (multipart/form-data)
export async function POST(request: NextRequest, context: RouteContext) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const { id } = await context.params;
    const productId = parseInt(id);

    if (isNaN(productId)) {
      return errorResponse("INVALID_ID", "Geçersiz ürün ID", undefined, 400);
    }

    // Check if product exists
    const product = await prisma.product.findUnique({
      where: { id: productId },
      include: { images: true },
    });

    if (!product) {
      return errorResponse("PRODUCT_NOT_FOUND", "Ürün bulunamadı", undefined, 404);
    }

    const formData = await request.formData();
    const file = formData.get("image") as File | null;
    const isPrimaryStr = formData.get("is_primary") as string | null;
    const isPrimary = isPrimaryStr === "true";

    if (!file) {
      return errorResponse("NO_FILE", "Görsel dosyası gerekli", undefined, 400);
    }

    // Validate file type
    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      return errorResponse(
        "INVALID_FILE_TYPE",
        "Geçersiz dosya tipi",
        "Sadece JPEG, PNG ve WebP desteklenir"
      );
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      return errorResponse(
        "FILE_TOO_LARGE",
        "Dosya çok büyük",
        "Maksimum 5MB desteklenir"
      );
    }

    // Convert to base64
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    const base64 = `data:${file.type};base64,${buffer.toString("base64")}`;

    // Upload to Cloudinary
    const uploadResult = await uploadImage(base64, "products");

    // If setting as primary, unset other primaries
    if (isPrimary) {
      await prisma.productImage.updateMany({
        where: { productId },
        data: { isPrimary: false },
      });
    }

    // Save to database
    const image = await prisma.productImage.create({
      data: {
        productId,
        imageUrl: uploadResult.url,
        isPrimary: isPrimary || product.images.length === 0, // First image is primary by default
        sortOrder: product.images.length,
      },
    });

    return successResponse(
      {
        id: image.id,
        url: image.imageUrl,
        isPrimary: image.isPrimary,
      },
      201
    );
  } catch (error) {
    console.error("Image upload error:", error);
    return errorResponse("UPLOAD_ERROR", "Görsel yüklenemedi", undefined, 500);
  }
}

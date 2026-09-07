import { NextRequest, NextResponse } from "next/server";
import { prisma } from "./prisma";

export interface AuthResult {
  success: boolean;
  error?: NextResponse;
}

export async function validateApiKey(request: NextRequest): Promise<AuthResult> {
  const authHeader = request.headers.get("authorization");

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return {
      success: false,
      error: NextResponse.json(
        {
          success: false,
          error: {
            code: "UNAUTHORIZED",
            message: "API anahtarı gerekli",
            details: "Authorization header'ında Bearer token gönderin",
          },
        },
        { status: 401 }
      ),
    };
  }

  const apiKey = authHeader.replace("Bearer ", "");

  // Önce env'deki sabit key'i kontrol et (development için)
  // Not: API_SECRET_KEY tanımsız/boşsa asla eşleşmemeli (boş Bearer token kabul edilmesin).
  if (process.env.API_SECRET_KEY && apiKey === process.env.API_SECRET_KEY) {
    return { success: true };
  }

  // Veritabanındaki API key'leri kontrol et
  try {
    const keyRecord = await prisma.apiKey.findUnique({
      where: { key: apiKey },
    });

    if (!keyRecord || !keyRecord.isActive) {
      return {
        success: false,
        error: NextResponse.json(
          {
            success: false,
            error: {
              code: "INVALID_API_KEY",
              message: "Geçersiz API anahtarı",
            },
          },
          { status: 401 }
        ),
      };
    }

    // Son kullanım zamanını güncelle
    await prisma.apiKey.update({
      where: { id: keyRecord.id },
      data: { lastUsedAt: new Date() },
    });

    return { success: true };
  } catch {
    return {
      success: false,
      error: NextResponse.json(
        {
          success: false,
          error: {
            code: "AUTH_ERROR",
            message: "Kimlik doğrulama hatası",
          },
        },
        { status: 500 }
      ),
    };
  }
}

// API yanıtı için yardımcı fonksiyonlar
export function successResponse<T>(data: T, status = 200) {
  return NextResponse.json({ success: true, data }, { status });
}

export function errorResponse(
  code: string,
  message: string,
  details?: string,
  status = 400
) {
  return NextResponse.json(
    {
      success: false,
      error: { code, message, details },
    },
    { status }
  );
}

export function paginatedResponse<T>(
  data: T[],
  page: number,
  limit: number,
  totalItems: number
) {
  return NextResponse.json({
    success: true,
    data,
    pagination: {
      page,
      limit,
      totalItems,
      totalPages: Math.ceil(totalItems / limit),
    },
  });
}

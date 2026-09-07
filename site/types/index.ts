// ==========================================
// VERİTABANI TİPLERİ
// ==========================================

export interface Category {
  id: number;
  name: string;
  slug: string;
  parentId: number | null;
  isActive: boolean;
  createdAt: Date;
  productCount?: number;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  categoryId: number | null;
  price: number;
  costPrice: number | null;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  category?: Category | null;
  variants?: ProductVariant[];
  images?: ProductImage[];
  primaryImage?: string;
  totalStock?: number;
}

export interface ProductVariant {
  id: number;
  productId: number;
  size: string | null;
  color: string | null;
  stock: number;
  barcode: string | null;
  product?: Product;
}

export interface ProductImage {
  id: number;
  productId: number;
  imageUrl: string;
  isPrimary: boolean;
  sortOrder: number;
}

export interface Sale {
  id: number;
  saleDate: Date;
  totalAmount: number;
  paymentMethod: string | null;
  notes: string | null;
  source: string;
  items?: SaleItem[];
}

export interface SaleItem {
  id: number;
  saleId: number;
  variantId: number | null;
  productName: string;
  size: string | null;
  color: string | null;
  quantity: number;
  unitPrice: number;
  variant?: ProductVariant;
}

export interface StockLog {
  id: number;
  variantId: number;
  changeType: string;
  quantityChange: number;
  previousStock: number;
  newStock: number;
  note: string | null;
  createdAt: Date;
}

// ==========================================
// API REQUEST/RESPONSE TİPLERİ
// ==========================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: string;
  };
  pagination?: {
    page: number;
    limit: number;
    totalItems: number;
    totalPages: number;
  };
}

// Ürün API'leri
export interface CreateProductRequest {
  sku: string;
  name: string;
  description?: string;
  price: number;
  costPrice?: number;
  categoryId?: number;
  variants?: {
    size?: string;
    color?: string;
    stock: number;
    barcode?: string;
  }[];
}

export interface UpdateProductRequest {
  name?: string;
  description?: string;
  price?: number;
  costPrice?: number;
  categoryId?: number;
  isActive?: boolean;
}

// Stok API'leri
export interface StockUpdateRequest {
  variantId?: number;
  sku?: string;
  size?: string;
  color?: string;
  change: number;
  reason: "sale" | "restock" | "adjustment" | "return";
  note?: string;
}

export interface StockQueryResponse {
  variantId: number;
  productSku: string;
  productName: string;
  size: string | null;
  color: string | null;
  stock: number;
}

// Satış API'leri
export interface CreateSaleRequest {
  paymentMethod?: "cash" | "card";
  items: {
    sku: string;
    size?: string;
    color?: string;
    quantity: number;
    unitPrice: number;
  }[];
  notes?: string;
}

// Rapor API'leri
export interface DailyReportResponse {
  date: string;
  summary: {
    totalSales: number;
    totalRevenue: number;
    totalProfit: number;
    totalItemsSold: number;
  };
  paymentBreakdown: {
    cash: number;
    card: number;
  };
  topProducts: {
    sku: string;
    name: string;
    quantitySold: number;
    revenue: number;
  }[];
  sales: {
    id: number;
    time: string;
    amount: number;
    items: number;
  }[];
}

export interface MonthlyReportResponse {
  period: string;
  summary: {
    totalSales: number;
    totalRevenue: number;
    totalProfit: number;
    totalItemsSold: number;
    averageDaily: number;
    averageOrder: number;
  };
  comparison?: {
    previousMonthRevenue: number;
    changeAmount: number;
    changePercent: number;
  };
  bestDay?: {
    date: string;
    revenue: number;
  };
  worstDay?: {
    date: string;
    revenue: number;
  };
  categoryBreakdown: {
    category: string;
    revenue: number;
    percent: number;
  }[];
  topProducts: {
    sku: string;
    name: string;
    quantitySold: number;
    revenue: number;
  }[];
  paymentBreakdown: {
    cash: number;
    card: number;
  };
}

// ==========================================
// FRONTEND TİPLERİ
// ==========================================

export interface CartItem {
  id: string; // variantId veya benzersiz key
  productId: number;
  sku: string;
  name: string;
  size: string | null;
  color: string | null;
  price: number;
  quantity: number;
  image: string;
  maxStock: number;
}

export interface CartState {
  items: CartItem[];
  totalItems: number;
  totalPrice: number;
}

// Filter types
export interface ProductFilters {
  search?: string;
  categoryId?: number;
  minPrice?: number;
  maxPrice?: number;
  sizes?: string[];
  colors?: string[];
  inStock?: boolean;
}

export interface SortOption {
  value: string;
  label: string;
}

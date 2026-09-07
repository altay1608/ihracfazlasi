-- Turso/libSQL Schema for İhraç Fazlası Giyim

-- Category table
CREATE TABLE IF NOT EXISTS Category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    parentId INTEGER,
    isActive INTEGER NOT NULL DEFAULT 1,
    createdAt TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (parentId) REFERENCES Category(id)
);

-- Product table
CREATE TABLE IF NOT EXISTS Product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    categoryId INTEGER,
    price REAL NOT NULL,
    costPrice REAL,
    isActive INTEGER NOT NULL DEFAULT 1,
    createdAt TEXT NOT NULL DEFAULT (datetime('now')),
    updatedAt TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (categoryId) REFERENCES Category(id)
);

-- ProductVariant table
CREATE TABLE IF NOT EXISTS ProductVariant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    productId INTEGER NOT NULL,
    size TEXT,
    color TEXT,
    stock INTEGER NOT NULL DEFAULT 0,
    barcode TEXT,
    FOREIGN KEY (productId) REFERENCES Product(id) ON DELETE CASCADE,
    UNIQUE(productId, size, color)
);

-- ProductImage table
CREATE TABLE IF NOT EXISTS ProductImage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    productId INTEGER NOT NULL,
    imageUrl TEXT NOT NULL,
    isPrimary INTEGER NOT NULL DEFAULT 0,
    sortOrder INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (productId) REFERENCES Product(id) ON DELETE CASCADE
);

-- Sale table
CREATE TABLE IF NOT EXISTS Sale (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    saleDate TEXT NOT NULL DEFAULT (datetime('now')),
    totalAmount REAL NOT NULL,
    paymentMethod TEXT,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'telegram'
);

-- SaleItem table
CREATE TABLE IF NOT EXISTS SaleItem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    saleId INTEGER NOT NULL,
    variantId INTEGER,
    productName TEXT NOT NULL,
    size TEXT,
    color TEXT,
    quantity INTEGER NOT NULL,
    unitPrice REAL NOT NULL,
    FOREIGN KEY (saleId) REFERENCES Sale(id) ON DELETE CASCADE,
    FOREIGN KEY (variantId) REFERENCES ProductVariant(id)
);

-- StockLog table
CREATE TABLE IF NOT EXISTS StockLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variantId INTEGER NOT NULL,
    changeType TEXT NOT NULL,
    quantityChange INTEGER NOT NULL,
    previousStock INTEGER NOT NULL,
    newStock INTEGER NOT NULL,
    note TEXT,
    createdAt TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (variantId) REFERENCES ProductVariant(id) ON DELETE CASCADE
);

-- ApiKey table
CREATE TABLE IF NOT EXISTS ApiKey (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    isActive INTEGER NOT NULL DEFAULT 1,
    createdAt TEXT NOT NULL DEFAULT (datetime('now')),
    lastUsedAt TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_product_category ON Product(categoryId);
CREATE INDEX IF NOT EXISTS idx_product_sku ON Product(sku);
CREATE INDEX IF NOT EXISTS idx_variant_product ON ProductVariant(productId);
CREATE INDEX IF NOT EXISTS idx_sale_date ON Sale(saleDate);
CREATE INDEX IF NOT EXISTS idx_saleitem_sale ON SaleItem(saleId);
CREATE INDEX IF NOT EXISTS idx_stocklog_variant ON StockLog(variantId);

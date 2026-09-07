import { createClient } from "@libsql/client";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { config } from "dotenv";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env file
config({ path: join(__dirname, "..", ".env") });

const client = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN,
});

async function seed() {
  console.log("🌱 Turso veritabanına örnek veriler ekleniyor...\n");

  // Kategoriler
  const categories = [
    { name: "Elbiseler", slug: "elbiseler" },
    { name: "Gömlekler", slug: "gomlekler" },
    { name: "Pantolonlar", slug: "pantolonlar" },
    { name: "Ceketler", slug: "ceketler" },
    { name: "Kazaklar", slug: "kazaklar" },
    { name: "Etekler", slug: "etekler" },
  ];

  console.log("📁 Kategoriler ekleniyor...");
  for (const cat of categories) {
    try {
      await client.execute({
        sql: "INSERT OR IGNORE INTO Category (name, slug) VALUES (?, ?)",
        args: [cat.name, cat.slug],
      });
      console.log(`   ✅ ${cat.name}`);
    } catch (error) {
      console.log(`   ⚠️ ${cat.name} - ${error.message}`);
    }
  }

  // Kategori ID'lerini al
  const catResult = await client.execute("SELECT id, slug FROM Category");
  const categoryMap = {};
  catResult.rows.forEach((row) => {
    categoryMap[row.slug] = row.id;
  });
  console.log("\n📋 Kategori ID'leri:", categoryMap);

  // Ürünler
  const products = [
    // Elbiseler
    {
      sku: "ELB001",
      name: "Yazlık Çiçekli Elbise",
      description: "Hafif kumaştan yazlık çiçek desenli elbise. Rahat kesim.",
      price: 450,
      costPrice: 180,
      categorySlug: "elbiseler",
      variants: [
        { size: "S", color: "Kırmızı", stock: 5 },
        { size: "M", color: "Kırmızı", stock: 8 },
        { size: "L", color: "Kırmızı", stock: 6 },
        { size: "XL", color: "Kırmızı", stock: 4 },
      ],
    },
    {
      sku: "ELB002",
      name: "Pamuklu Midi Elbise",
      description: "100% pamuklu, günlük kullanıma uygun midi boy elbise.",
      price: 380,
      costPrice: 150,
      categorySlug: "elbiseler",
      variants: [
        { size: "S", color: "Siyah", stock: 10 },
        { size: "M", color: "Siyah", stock: 10 },
        { size: "L", color: "Siyah", stock: 8 },
        { size: "XL", color: "Siyah", stock: 5 },
      ],
    },
    // Gömlekler
    {
      sku: "GML001",
      name: "Beyaz Keten Gömlek",
      description: "Saf keten kumaştan, yaz sıcaklarına ideal beyaz gömlek.",
      price: 320,
      costPrice: 130,
      categorySlug: "gomlekler",
      variants: [
        { size: "S", color: "Beyaz", stock: 10 },
        { size: "M", color: "Beyaz", stock: 10 },
        { size: "L", color: "Beyaz", stock: 10 },
        { size: "XL", color: "Beyaz", stock: 8 },
      ],
    },
    {
      sku: "GML002",
      name: "Oversize Denim Gömlek",
      description: "Rahat kesim, yıkamalı denim gömlek.",
      price: 280,
      costPrice: 110,
      categorySlug: "gomlekler",
      variants: [
        { size: "S", color: "Mavi", stock: 8 },
        { size: "M", color: "Mavi", stock: 10 },
        { size: "L", color: "Mavi", stock: 10 },
        { size: "XL", color: "Mavi", stock: 6 },
      ],
    },
    // Pantolonlar
    {
      sku: "PNT001",
      name: "Yüksek Bel Wide Leg Pantolon",
      description: "Yüksek bel, geniş paça, şık ve rahat pantolon.",
      price: 420,
      costPrice: 170,
      categorySlug: "pantolonlar",
      variants: [
        { size: "S", color: "Siyah", stock: 6 },
        { size: "M", color: "Siyah", stock: 10 },
        { size: "L", color: "Siyah", stock: 8 },
        { size: "XL", color: "Siyah", stock: 5 },
      ],
    },
    {
      sku: "PNT002",
      name: "Slim Fit Kumaş Pantolon",
      description: "Ofis ve özel günler için ideal slim fit kesim pantolon.",
      price: 350,
      costPrice: 140,
      categorySlug: "pantolonlar",
      variants: [
        { size: "S", color: "Lacivert", stock: 7 },
        { size: "M", color: "Lacivert", stock: 10 },
        { size: "L", color: "Lacivert", stock: 9 },
        { size: "XL", color: "Lacivert", stock: 5 },
      ],
    },
    // Ceketler
    {
      sku: "CKT001",
      name: "Oversize Blazer Ceket",
      description: "Trend oversize kesim, her kombine uyumlu blazer ceket.",
      price: 680,
      costPrice: 280,
      categorySlug: "ceketler",
      variants: [
        { size: "S", color: "Siyah", stock: 5 },
        { size: "M", color: "Siyah", stock: 8 },
        { size: "L", color: "Siyah", stock: 6 },
        { size: "XL", color: "Siyah", stock: 4 },
      ],
    },
    {
      sku: "CKT002",
      name: "Deri Ceket",
      description: "Kaliteli suni deri, klasik kesim motor ceket.",
      price: 850,
      costPrice: 350,
      categorySlug: "ceketler",
      variants: [
        { size: "S", color: "Siyah", stock: 4 },
        { size: "M", color: "Siyah", stock: 6 },
        { size: "L", color: "Siyah", stock: 5 },
        { size: "XL", color: "Siyah", stock: 3 },
      ],
    },
    // Kazaklar
    {
      sku: "KZK001",
      name: "Boğazlı Triko Kazak",
      description: "Yumuşak triko, boğazlı yaka, kış ayları için ideal.",
      price: 290,
      costPrice: 115,
      categorySlug: "kazaklar",
      variants: [
        { size: "S", color: "Bej", stock: 8 },
        { size: "M", color: "Bej", stock: 10 },
        { size: "L", color: "Bej", stock: 10 },
        { size: "XL", color: "Bej", stock: 6 },
      ],
    },
    {
      sku: "KZK002",
      name: "Oversize Örme Kazak",
      description: "Kalın örme, rahat oversize kesim kazak.",
      price: 340,
      costPrice: 135,
      categorySlug: "kazaklar",
      variants: [
        { size: "S", color: "Gri", stock: 6 },
        { size: "M", color: "Gri", stock: 8 },
        { size: "L", color: "Gri", stock: 8 },
        { size: "XL", color: "Gri", stock: 5 },
      ],
    },
    // Etekler
    {
      sku: "ETK001",
      name: "Pileli Midi Etek",
      description: "Zarif pileli kesim, midi boy şık etek.",
      price: 290,
      costPrice: 115,
      categorySlug: "etekler",
      variants: [
        { size: "S", color: "Bordo", stock: 6 },
        { size: "M", color: "Bordo", stock: 8 },
        { size: "L", color: "Bordo", stock: 5 },
        { size: "XL", color: "Bordo", stock: 4 },
      ],
    },
    {
      sku: "ETK002",
      name: "Denim Mini Etek",
      description: "Klasik denim, A kesim mini etek.",
      price: 220,
      costPrice: 90,
      categorySlug: "etekler",
      variants: [
        { size: "S", color: "Mavi", stock: 10 },
        { size: "M", color: "Mavi", stock: 10 },
        { size: "L", color: "Mavi", stock: 8 },
        { size: "XL", color: "Mavi", stock: 5 },
      ],
    },
  ];

  console.log("\n📦 Ürünler ekleniyor...");
  for (const product of products) {
    try {
      const categoryId = categoryMap[product.categorySlug] || null;

      await client.execute({
        sql: `INSERT OR IGNORE INTO Product (sku, name, description, price, costPrice, categoryId)
              VALUES (?, ?, ?, ?, ?, ?)`,
        args: [product.sku, product.name, product.description, product.price, product.costPrice, categoryId],
      });

      const productResult = await client.execute({
        sql: "SELECT id FROM Product WHERE sku = ?",
        args: [product.sku],
      });

      if (productResult.rows.length === 0) {
        console.log(`   ⚠️ ${product.name} - Ürün bulunamadı`);
        continue;
      }

      const productId = productResult.rows[0].id;
      console.log(`   ✅ ${product.name} (${product.sku})`);

      for (const variant of product.variants) {
        try {
          await client.execute({
            sql: `INSERT OR IGNORE INTO ProductVariant (productId, size, color, stock)
                  VALUES (?, ?, ?, ?)`,
            args: [productId, variant.size, variant.color, variant.stock],
          });
        } catch (error) {
          // Ignore duplicate variants
        }
      }
    } catch (error) {
      console.log(`   ❌ ${product.name} - ${error.message}`);
    }
  }

  // API Key ekle
  console.log("\n🔑 API Key ekleniyor...");
  try {
    await client.execute({
      sql: "INSERT OR IGNORE INTO ApiKey (key, name) VALUES (?, ?)",
      args: ["ihrac-fazlasi-api-key-2026", "Default API Key"],
    });
    console.log("   ✅ Default API Key eklendi");
  } catch (error) {
    console.log(`   ⚠️ API Key - ${error.message}`);
  }

  // Sonuçları göster
  console.log("\n📊 Veritabanı Durumu:");

  const catCount = await client.execute("SELECT COUNT(*) as count FROM Category");
  console.log(`   Kategoriler: ${catCount.rows[0].count}`);

  const prodCount = await client.execute("SELECT COUNT(*) as count FROM Product");
  console.log(`   Ürünler: ${prodCount.rows[0].count}`);

  const varCount = await client.execute("SELECT COUNT(*) as count FROM ProductVariant");
  console.log(`   Varyantlar: ${varCount.rows[0].count}`);

  const totalStock = await client.execute("SELECT SUM(stock) as total FROM ProductVariant");
  console.log(`   Toplam Stok: ${totalStock.rows[0].total || 0} adet`);

  console.log("\n✅ Seed tamamlandı!");
  await client.close();
}

seed().catch(console.error);

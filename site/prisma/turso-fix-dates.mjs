import { createClient } from "@libsql/client";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { config } from "dotenv";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

config({ path: join(__dirname, "..", ".env") });

const client = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN,
});

async function fixDates() {
  console.log("🔧 Tarih formatları düzeltiliyor...\n");

  // Category tablosu
  console.log("📁 Category tablosu...");
  await client.execute(`
    UPDATE Category
    SET createdAt = replace(createdAt, ' ', 'T') || '.000Z'
    WHERE createdAt NOT LIKE '%T%'
  `);
  console.log("   ✅ Category.createdAt düzeltildi");

  // Product tablosu
  console.log("\n📦 Product tablosu...");
  await client.execute(`
    UPDATE Product
    SET createdAt = replace(createdAt, ' ', 'T') || '.000Z'
    WHERE createdAt NOT LIKE '%T%'
  `);
  console.log("   ✅ Product.createdAt düzeltildi");

  await client.execute(`
    UPDATE Product
    SET updatedAt = replace(updatedAt, ' ', 'T') || '.000Z'
    WHERE updatedAt NOT LIKE '%T%'
  `);
  console.log("   ✅ Product.updatedAt düzeltildi");

  // Sale tablosu
  console.log("\n💰 Sale tablosu...");
  await client.execute(`
    UPDATE Sale
    SET saleDate = replace(saleDate, ' ', 'T') || '.000Z'
    WHERE saleDate NOT LIKE '%T%'
  `);
  console.log("   ✅ Sale.saleDate düzeltildi");

  // StockLog tablosu
  console.log("\n📊 StockLog tablosu...");
  await client.execute(`
    UPDATE StockLog
    SET createdAt = replace(createdAt, ' ', 'T') || '.000Z'
    WHERE createdAt NOT LIKE '%T%'
  `);
  console.log("   ✅ StockLog.createdAt düzeltildi");

  // ApiKey tablosu
  console.log("\n🔑 ApiKey tablosu...");
  await client.execute(`
    UPDATE ApiKey
    SET createdAt = replace(createdAt, ' ', 'T') || '.000Z'
    WHERE createdAt NOT LIKE '%T%'
  `);
  console.log("   ✅ ApiKey.createdAt düzeltildi");

  // Kontrol
  console.log("\n📋 Kontrol:");
  const category = await client.execute("SELECT createdAt FROM Category LIMIT 1");
  console.log(`   Category.createdAt: ${category.rows[0]?.createdAt}`);

  const product = await client.execute("SELECT createdAt, updatedAt FROM Product LIMIT 1");
  console.log(`   Product.createdAt: ${product.rows[0]?.createdAt}`);
  console.log(`   Product.updatedAt: ${product.rows[0]?.updatedAt}`);

  console.log("\n✅ Tarih formatları düzeltildi!");
  await client.close();
}

fixDates().catch(console.error);

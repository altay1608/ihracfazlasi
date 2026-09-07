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

async function addIndex() {
  console.log("🔧 Expense category index ekleniyor...\n");

  try {
    await client.execute(`
      CREATE INDEX IF NOT EXISTS idx_expense_category ON Expense(category)
    `);
    console.log("✅ idx_expense_category index oluşturuldu");
  } catch (error) {
    console.log("⚠️ Index zaten var veya hata:", error.message);
  }

  // Tablo yapısını kontrol et
  const info = await client.execute("PRAGMA table_info(Expense)");
  console.log("\n📋 Expense tablo yapısı:");
  info.rows.forEach(row => {
    console.log(`   ${row.name} (${row.type})${row.notnull ? " NOT NULL" : ""}${row.pk ? " PRIMARY KEY" : ""}`);
  });

  await client.close();
}

addIndex().catch(console.error);

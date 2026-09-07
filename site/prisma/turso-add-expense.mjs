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

async function addExpenseTable() {
  console.log("🔧 Expense tablosu ekleniyor...\n");

  // Expense tablosu
  await client.execute(`
    CREATE TABLE IF NOT EXISTS Expense (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      amount REAL NOT NULL,
      category TEXT NOT NULL,
      description TEXT,
      expenseDate TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S.000Z', 'now')),
      createdAt TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S.000Z', 'now'))
    )
  `);
  console.log("✅ Expense tablosu oluşturuldu");

  // Index
  await client.execute(`
    CREATE INDEX IF NOT EXISTS idx_expense_date ON Expense(expenseDate)
  `);
  console.log("✅ Index oluşturuldu");

  // Kontrol
  const tables = await client.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='Expense'"
  );
  console.log("\n📋 Tablo kontrolü:", tables.rows.length > 0 ? "Expense tablosu mevcut" : "Hata!");

  console.log("\n✅ Expense tablosu eklendi!");
  await client.close();
}

addExpenseTable().catch(console.error);

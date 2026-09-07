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

async function simplifyCategories() {
  console.log("🗂️ Kategoriler sadeleştiriliyor...\n");

  // 3 ana kategori
  const mainCategories = [
    { name: "Üst Giyim", slug: "ust-giyim" },
    { name: "Alt Giyim", slug: "alt-giyim" },
    { name: "Aksesuar", slug: "aksesuar" },
  ];

  // Önce ana kategorilerin var olduğundan emin ol
  console.log("📁 Ana kategoriler oluşturuluyor...");
  for (const cat of mainCategories) {
    try {
      await client.execute({
        sql: "INSERT OR IGNORE INTO Category (name, slug, isActive) VALUES (?, ?, 1)",
        args: [cat.name, cat.slug],
      });
      console.log(`   ✅ ${cat.name} (${cat.slug})`);
    } catch (error) {
      console.log(`   ⚠️ ${cat.name} - ${error.message}`);
    }
  }

  // Mevcut kategorileri listele
  console.log("\n📋 Mevcut kategoriler:");
  const existingCats = await client.execute("SELECT id, name, slug FROM Category ORDER BY name");
  for (const row of existingCats.rows) {
    console.log(`   - ${row.name} (${row.slug}) [ID: ${row.id}]`);
  }

  // Üst Giyim ID'sini al
  const ustGiyimResult = await client.execute({
    sql: "SELECT id FROM Category WHERE slug = ?",
    args: ["ust-giyim"],
  });
  const ustGiyimId = ustGiyimResult.rows[0]?.id;

  // Alt Giyim ID'sini al
  const altGiyimResult = await client.execute({
    sql: "SELECT id FROM Category WHERE slug = ?",
    args: ["alt-giyim"],
  });
  const altGiyimId = altGiyimResult.rows[0]?.id;

  // Aksesuar ID'sini al
  const aksesuarResult = await client.execute({
    sql: "SELECT id FROM Category WHERE slug = ?",
    args: ["aksesuar"],
  });
  const aksesuarId = aksesuarResult.rows[0]?.id;

  console.log(`\n🔄 Kategori eşleştirmeleri: Üst Giyim=${ustGiyimId}, Alt Giyim=${altGiyimId}, Aksesuar=${aksesuarId}`);

  // Üst giyim kategorileri (taşınacak)
  const ustGiyimSlugs = ["gomlekler", "tisortler", "ceketler", "kazaklar", "montlar", "elbiseler", "etekler"];

  // Alt giyim kategorileri (taşınacak)
  const altGiyimSlugs = ["pantolonlar", "takim-elbise"];

  // Ürünleri Üst Giyim'e taşı
  if (ustGiyimId) {
    console.log("\n🔄 Üst giyim ürünleri taşınıyor...");
    for (const slug of ustGiyimSlugs) {
      const catResult = await client.execute({
        sql: "SELECT id FROM Category WHERE slug = ?",
        args: [slug],
      });

      if (catResult.rows.length > 0) {
        const oldCatId = catResult.rows[0].id;
        const updateResult = await client.execute({
          sql: "UPDATE Product SET categoryId = ? WHERE categoryId = ?",
          args: [ustGiyimId, oldCatId],
        });
        console.log(`   📦 ${slug} -> Üst Giyim (${updateResult.rowsAffected} ürün)`);
      }
    }
  }

  // Ürünleri Alt Giyim'e taşı
  if (altGiyimId) {
    console.log("\n🔄 Alt giyim ürünleri taşınıyor...");
    for (const slug of altGiyimSlugs) {
      const catResult = await client.execute({
        sql: "SELECT id FROM Category WHERE slug = ?",
        args: [slug],
      });

      if (catResult.rows.length > 0) {
        const oldCatId = catResult.rows[0].id;
        const updateResult = await client.execute({
          sql: "UPDATE Product SET categoryId = ? WHERE categoryId = ?",
          args: [altGiyimId, oldCatId],
        });
        console.log(`   📦 ${slug} -> Alt Giyim (${updateResult.rowsAffected} ürün)`);
      }
    }
  }

  // Eski kategorileri sil (3 ana kategori dışındakileri)
  console.log("\n🗑️ Eski kategoriler siliniyor...");
  const deleteResult = await client.execute({
    sql: "DELETE FROM Category WHERE slug NOT IN ('ust-giyim', 'alt-giyim', 'aksesuar')",
    args: [],
  });
  console.log(`   ✅ ${deleteResult.rowsAffected} kategori silindi`);

  // Sonuçları göster
  console.log("\n📊 Güncel Durum:");

  const finalCats = await client.execute("SELECT id, name, slug FROM Category ORDER BY name");
  console.log("\n   Kategoriler:");
  for (const row of finalCats.rows) {
    const countResult = await client.execute({
      sql: "SELECT COUNT(*) as count FROM Product WHERE categoryId = ?",
      args: [row.id],
    });
    console.log(`   - ${row.name} (${countResult.rows[0].count} ürün)`);
  }

  console.log("\n✅ Kategori sadeleştirme tamamlandı!");
  await client.close();
}

simplifyCategories().catch(console.error);

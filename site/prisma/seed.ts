import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("Seeding database...");

  // Create main categories (simplified - only 3)
  const categories = await Promise.all([
    prisma.category.upsert({
      where: { slug: "ust-giyim" },
      update: { name: "Üst Giyim" },
      create: { name: "Üst Giyim", slug: "ust-giyim" },
    }),
    prisma.category.upsert({
      where: { slug: "alt-giyim" },
      update: { name: "Alt Giyim" },
      create: { name: "Alt Giyim", slug: "alt-giyim" },
    }),
    prisma.category.upsert({
      where: { slug: "aksesuar" },
      update: { name: "Aksesuar" },
      create: { name: "Aksesuar", slug: "aksesuar" },
    }),
  ]);

  console.log(`Created ${categories.length} categories`);

  // Sample products data - using new simplified categories
  const productsData = [
    {
      sku: "LCST01",
      name: "Lacoste Erkek Beyaz Polo T-Shirt",
      description: "Orijinal Lacoste polo yaka erkek t-shirt. Premium pamuklu kumaş.",
      price: 450,
      costPrice: 180,
      categorySlug: "ust-giyim",
      variants: [
        { size: "S", color: "Standart", stock: 5 },
        { size: "M", color: "Standart", stock: 8 },
        { size: "L", color: "Standart", stock: 3 },
        { size: "XL", color: "Standart", stock: 4 },
      ],
      images: [
        "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=800&h=1000&fit=crop",
      ],
    },
    {
      sku: "TH01",
      name: "Tommy Hilfiger Erkek Lacivert Slim Fit Gömlek",
      description: "Tommy Hilfiger slim fit erkek gömlek. %100 pamuk.",
      price: 380,
      costPrice: 150,
      categorySlug: "ust-giyim",
      variants: [
        { size: "S", color: "Standart", stock: 10 },
        { size: "M", color: "Standart", stock: 12 },
        { size: "L", color: "Standart", stock: 8 },
        { size: "XL", color: "Standart", stock: 5 },
      ],
      images: [
        "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=800&h=1000&fit=crop",
      ],
    },
    {
      sku: "HB01",
      name: "Hugo Boss Erkek Siyah Kazak",
      description: "Hugo Boss premium yün karışımlı erkek kazak.",
      price: 680,
      costPrice: 280,
      categorySlug: "ust-giyim",
      variants: [
        { size: "S", color: "Standart", stock: 4 },
        { size: "M", color: "Standart", stock: 6 },
        { size: "L", color: "Standart", stock: 5 },
        { size: "XL", color: "Standart", stock: 3 },
      ],
      images: [
        "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&h=1000&fit=crop",
      ],
    },
    {
      sku: "CK01",
      name: "Calvin Klein Erkek Gri Slim Fit Pantolon",
      description: "Calvin Klein slim fit erkek pantolon. Şık ve rahat.",
      price: 420,
      costPrice: 170,
      categorySlug: "alt-giyim",
      variants: [
        { size: "S", color: "Standart", stock: 6 },
        { size: "M", color: "Standart", stock: 10 },
        { size: "L", color: "Standart", stock: 8 },
        { size: "XL", color: "Standart", stock: 5 },
      ],
      images: [
        "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=800&h=1000&fit=crop",
      ],
    },
    {
      sku: "RL01",
      name: "Ralph Lauren Erkek Lacivert Chino Pantolon",
      description: "Ralph Lauren klasik chino pantolon. Premium kalite.",
      price: 350,
      costPrice: 140,
      categorySlug: "alt-giyim",
      variants: [
        { size: "S", color: "Standart", stock: 7 },
        { size: "M", color: "Standart", stock: 12 },
        { size: "L", color: "Standart", stock: 9 },
        { size: "XL", color: "Standart", stock: 5 },
      ],
      images: [
        "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=800&h=1000&fit=crop",
      ],
    },
    {
      sku: "ARM01",
      name: "Armani Erkek Siyah Deri Kemer",
      description: "Emporio Armani hakiki deri erkek kemer.",
      price: 290,
      costPrice: 115,
      categorySlug: "aksesuar",
      variants: [
        { size: "M", color: "Standart", stock: 8 },
        { size: "L", color: "Standart", stock: 10 },
        { size: "XL", color: "Standart", stock: 5 },
      ],
      images: [
        "https://images.unsplash.com/photo-1553062407-98eeb64c6a45?w=800&h=1000&fit=crop",
      ],
    },
  ];

  // Create products
  for (const data of productsData) {
    const category = categories.find((c) => c.slug === data.categorySlug);

    const product = await prisma.product.upsert({
      where: { sku: data.sku },
      update: {},
      create: {
        sku: data.sku,
        name: data.name,
        description: data.description,
        price: data.price,
        costPrice: data.costPrice,
        categoryId: category?.id,
        variants: {
          create: data.variants,
        },
        images: {
          create: data.images.map((url, index) => ({
            imageUrl: url,
            isPrimary: index === 0,
            sortOrder: index,
          })),
        },
      },
    });

    console.log(`Created product: ${product.name}`);
  }

  // Create API key
  await prisma.apiKey.upsert({
    where: { key: "ihrac-fazlasi-api-key-2026" },
    update: {},
    create: {
      key: "ihrac-fazlasi-api-key-2026",
      name: "Default API Key",
    },
  });

  console.log("Created default API key");

  console.log("Database seeded successfully!");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

import type { NextConfig } from "next";
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const nextConfig: NextConfig = {
  // Disable automatic trailing slash redirect — middleware handles this,
  // and /panel/* routes need trailing slashes to reach Flask correctly.
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "res.cloudinary.com",
      },
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  serverExternalPackages: ["@libsql/client", "@prisma/adapter-libsql"],

  // 301 Yönlendirmeler - Eski URL'lerden yeni URL'lere
  async redirects() {
    return [
      // Eski ?product/ID formatından yeni /urunler formatına
      // Not: Query string redirect'leri için middleware kullanılmalı
      // Burası path-based redirect'ler için
      {
        source: "/product/:id",
        destination: "/urunler",
        permanent: true, // 301 redirect
      },
      {
        source: "/products/:path*",
        destination: "/urunler/:path*",
        permanent: true,
      },
      {
        source: "/category/:slug",
        destination: "/kategori/:slug",
        permanent: true,
      },
      {
        source: "/categories/:slug",
        destination: "/kategori/:slug",
        permanent: true,
      },
      {
        source: "/about",
        destination: "/hakkimizda",
        permanent: true,
      },
      {
        source: "/faq",
        destination: "/sss",
        permanent: true,
      },
    ];
  },

  webpack: (config) => {
    config.module.rules.push({
      test: /\.md$/,
      type: "asset/source",
    });
    config.resolve.alias = {
      ...config.resolve.alias,
    };
    config.externals = [...(config.externals || []), "@libsql/client"];
    return config;
  },
};

export default withBundleAnalyzer(nextConfig);

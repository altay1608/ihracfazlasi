import { Metadata } from "next";
import { SITE_CONFIG } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Sepetim",
  description: "Alışveriş sepetinizi görüntüleyin ve WhatsApp üzerinden sipariş verin.",
  alternates: {
    canonical: `${SITE_CONFIG.url}/sepet`,
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function SepetLayout({ children }: { children: React.ReactNode }) {
  return children;
}

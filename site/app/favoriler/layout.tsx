import { Metadata } from "next";
import { SITE_CONFIG } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Favorilerim",
  description: "Favori ürünlerinizi görüntüleyin. İhraç fazlası dünya markalarından beğendiğiniz ürünler.",
  alternates: {
    canonical: `${SITE_CONFIG.url}/favoriler`,
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function FavorilerLayout({ children }: { children: React.ReactNode }) {
  return children;
}

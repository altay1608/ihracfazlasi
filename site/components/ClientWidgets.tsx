"use client";

import dynamic from "next/dynamic";

// Lazy load widgets that appear after initial page load
const WhatsAppWidget = dynamic(() => import("@/components/WhatsAppWidget"), {
  ssr: false,
});

const StickyCartBar = dynamic(() => import("@/components/StickyCartBar"), {
  ssr: false,
});

export default function ClientWidgets() {
  return (
    <>
      <WhatsAppWidget />
      <StickyCartBar />
    </>
  );
}

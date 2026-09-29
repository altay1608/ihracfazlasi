const WEBHOOK_PATH = "/api/telegram/webhook";

export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  const botToken = process.env.TELEGRAM_BOT_TOKEN?.trim();
  const webhookSecret = process.env.TELEGRAM_WEBHOOK_SECRET?.trim();
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim();

  if (!botToken || !webhookSecret || !siteUrl) {
    console.warn(
      "Telegram webhook kurulumu atlandı: gerekli ortam değişkenleri eksik.",
    );
    return;
  }

  const webhookUrl = `${siteUrl.replace(/\/$/, "")}${WEBHOOK_PATH}`;

  try {
    const response = await fetch(
      `https://api.telegram.org/bot${botToken}/setWebhook`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: webhookUrl,
          allowed_updates: ["message"],
          secret_token: webhookSecret,
        }),
      },
    );
    const result = (await response.json()) as {
      ok?: boolean;
      description?: string;
    };

    if (!response.ok || !result.ok) {
      console.error(
        "Telegram webhook kurulamadı:",
        result.description || `HTTP ${response.status}`,
      );
      return;
    }

    console.info("Telegram webhook başarıyla doğrulandı.");
  } catch (error) {
    console.error(
      "Telegram webhook kurulumu sırasında bağlantı hatası:",
      error instanceof Error ? error.message : "Bilinmeyen hata",
    );
  }
}

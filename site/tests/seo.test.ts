import assert from "node:assert/strict";
import { test } from "node:test";
import { categoryIntro, pageNumber, serializeJsonLd } from "../lib/seo";
import { SITE_CONFIG } from "../lib/constants";
import robots from "../app/robots";
import config from "../next.config";

test("canonical URLs use the public domain, not Vercel deployment URLs", () => {
  assert.equal(SITE_CONFIG.url, (process.env.NEXT_PUBLIC_SITE_URL || "https://ihracfazlasigiyim.com").replace(/\/+$/, ""));
  assert.equal(new URL(SITE_CONFIG.url).protocol, "https:");
});

test("Google can crawl paginated listings and read noindex on filters", () => {
  const rules = robots().rules;
  assert.ok(Array.isArray(rules));
  const blocked = rules.flatMap(rule => rule.disallow || []);
  assert.ok(!blocked.some(path => path.includes("?") || path === "/"));
  assert.equal(robots().sitemap, `${SITE_CONFIG.url}/sitemap.xml`);
});

test("management and API routes have noindex response headers", async () => {
  const headers = await config.headers!();
  for (const source of ["/admin/:path*", "/panel/:path*", "/api/:path*"]) {
    assert.ok(headers.some(rule => rule.source === source && rule.headers.some(header => header.key === "X-Robots-Tag" && header.value.includes("noindex"))));
  }
  assert.ok(!headers.some(rule => rule.source === "/:path*" && rule.headers.some(header => header.key === "X-Robots-Tag")));
});

test("product text cannot terminate a structured data script", () => {
  const product = { name: '</script><script>alert("x")</script>' };
  const encoded = serializeJsonLd(product);
  assert.ok(!encoded.includes("<"));
  assert.deepEqual(JSON.parse(encoded), product);
});

test("invalid pagination cannot create NaN or negative canonical URLs", () => {
  for (const input of [undefined, "-1", "0", "abc", "2bad", "1.5", "Infinity"]) assert.equal(pageNumber(input), 1);
  assert.equal(pageNumber("2"), 2);
});

test("category introductions describe different collections", () => {
  const copy = ["ust-giyim", "alt-giyim", "aksesuar"].map(slug => categoryIntro(slug, slug));
  assert.equal(new Set(copy).size, 3);
  assert.ok(copy.every(text => text.includes("İnegöl")));
});

const ADMIN_COOKIE = 'admin-session';
const SESSION_LIFETIME_SECONDS = 60 * 60 * 8;

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function safeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function getAdminPassword(): string {
  return process.env.AUTH_PASSWORD || process.env.ADMIN_PASSWORD || '';
}

function getSigningSecret(): string {
  return process.env.ADMIN_SECRET || process.env.SECRET_KEY || getAdminPassword();
}

async function computeSignature(issuedAt: string): Promise<string> {
  const secret = getSigningSecret();
  if (!secret) return '';
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = await crypto.subtle.sign(
    'HMAC',
    key,
    new TextEncoder().encode(`admin-session:${issuedAt}`)
  );
  return toHex(new Uint8Array(signature));
}

export async function validateAdminSession(cookieValue: string): Promise<boolean> {
  if (!getAdminPassword() || !cookieValue) return false;
  const [issuedAt, signature, extra] = cookieValue.split('.');
  if (!issuedAt || !signature || extra) return false;

  const issuedAtSeconds = Number(issuedAt);
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (!Number.isInteger(issuedAtSeconds) || issuedAtSeconds > nowSeconds + 60) return false;
  if (nowSeconds - issuedAtSeconds > SESSION_LIFETIME_SECONDS) return false;

  const expectedSignature = await computeSignature(issuedAt);
  return Boolean(expectedSignature) && safeEqual(signature, expectedSignature);
}

export async function login(
  password: string
): Promise<{ success: true; token: string } | { success: false }> {
  const adminPassword = getAdminPassword();
  if (!adminPassword || !safeEqual(password, adminPassword)) return { success: false };
  const issuedAt = String(Math.floor(Date.now() / 1000));
  const signature = await computeSignature(issuedAt);
  if (!signature) return { success: false };
  return { success: true, token: `${issuedAt}.${signature}` };
}

export const ADMIN_COOKIE_NAME = ADMIN_COOKIE;

export const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  maxAge: SESSION_LIFETIME_SECONDS,
  path: '/',
};

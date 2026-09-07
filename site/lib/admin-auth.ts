const ADMIN_COOKIE = 'admin-session';
const DEFAULT_SALT = 'ihrac-admin-salt-2026';

async function computeToken(password: string): Promise<string> {
  const salt = process.env.ADMIN_SECRET || DEFAULT_SALT;
  const data = new TextEncoder().encode(password + salt);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export async function validateAdminSession(cookieValue: string): Promise<boolean> {
  const adminPassword = process.env.ADMIN_PASSWORD;
  if (!adminPassword || !cookieValue) return false;
  const expectedToken = await computeToken(adminPassword);
  return cookieValue === expectedToken;
}

export async function login(
  password: string
): Promise<{ success: true; token: string } | { success: false }> {
  const adminPassword = process.env.ADMIN_PASSWORD;
  if (!adminPassword || password !== adminPassword) return { success: false };
  const token = await computeToken(password);
  return { success: true, token };
}

export const ADMIN_COOKIE_NAME = ADMIN_COOKIE;

export const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  maxAge: 60 * 60 * 24 * 7,
  path: '/',
};

import { NextRequest, NextResponse } from 'next/server';

const FLASK_BASE = process.env.FLASK_URL || 'http://localhost:5000';
const PANEL_PREFIX = '/panel';

function rewriteLocation(location: string): string {
  if (location.startsWith(FLASK_BASE)) {
    const path = location.slice(FLASK_BASE.length) || '/';
    return PANEL_PREFIX + path;
  }
  if (location.startsWith('/') && !location.startsWith(PANEL_PREFIX)) {
    return PANEL_PREFIX + location;
  }
  return location;
}

function rewriteSetCookie(value: string): string {
  // Use Path=/panel (no trailing slash) so cookie is sent for both /panel and /panel/*
  return value.replace(/;\s*Path=\//gi, `; Path=${PANEL_PREFIX}`);
}

function rewriteHtml(html: string): string {
  return html
    .replace(
      /((?:href|action|src|hx-get|hx-post|hx-put|hx-delete|hx-patch)=")(\/)(?!\/|panel)/g,
      `$1${PANEL_PREFIX}/`
    )
    .replace(
      /((?:href|action|src|hx-get|hx-post|hx-put|hx-delete|hx-patch)=")(\/[^"#][^"]*?)(")/g,
      (match, before, path, after) => {
        if (path.startsWith(PANEL_PREFIX) || path.startsWith('//')) return match;
        return `${before}${PANEL_PREFIX}${path}${after}`;
      }
    );
}

// Follows Werkzeug's 308 trailing-slash redirects internally so the browser
// never sees the /panel/products/ ↔ /panel/products redirect loop.
async function fetchFlask(
  url: string,
  method: string,
  headers: Record<string, string>,
  body?: BodyInit
): Promise<Response> {
  let currentUrl = url;
  let currentBody: BodyInit | undefined = body;

  for (let i = 0; i < 5; i++) {
    const resp = await fetch(currentUrl, {
      method,
      headers,
      body: currentBody,
      redirect: 'manual',
      // @ts-expect-error - Node.js fetch extension
      duplex: currentBody ? 'half' : undefined,
    });

    // Werkzeug uses 308 for strict_slashes redirects — follow internally
    if (resp.status === 308) {
      const loc = resp.headers.get('location');
      if (!loc) return resp;
      const nextPath = loc.startsWith(FLASK_BASE)
        ? loc.slice(FLASK_BASE.length)
        : loc.startsWith('/') ? loc : null;
      if (!nextPath) return resp;
      const nextUrl = FLASK_BASE + nextPath;
      if (nextUrl === currentUrl) return resp; // prevent infinite loop
      currentUrl = nextUrl;
      currentBody = undefined; // 308 keeps method, but for GET navigation body is empty anyway
    } else {
      return resp;
    }
  }

  return fetch(currentUrl, { method, headers, redirect: 'manual' });
}

async function proxyRequest(request: NextRequest, slug: string[]): Promise<NextResponse> {
  const path = slug.length > 0 ? '/' + slug.join('/') : '/';
  const { search } = new URL(request.url);
  const targetUrl = FLASK_BASE + path + search;

  const clientIp = request.headers.get('x-forwarded-for') || '127.0.0.1';

  const forwardHeaders: Record<string, string> = {
    'X-Forwarded-For': clientIp,
    'X-Forwarded-Proto': 'http',
    'X-Real-IP': clientIp,
  };

  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (!['host', 'connection', 'transfer-encoding', 'content-length'].includes(lower)) {
      forwardHeaders[key] = value;
    }
  });

  try {
    let body: BodyInit | undefined = undefined;
    if (!['GET', 'HEAD'].includes(request.method)) {
      const buffer = await request.arrayBuffer();
      if (buffer.byteLength > 0) {
        body = buffer;
      }
    }

    const flaskResponse = await fetchFlask(targetUrl, request.method, forwardHeaders, body);

    const responseHeaders = new Headers();

    flaskResponse.headers.forEach((value, key) => {
      const lower = key.toLowerCase();

      if (['x-frame-options', 'transfer-encoding', 'connection', 'content-encoding', 'content-length'].includes(lower)) {
        return;
      }

      if (lower === 'location') {
        responseHeaders.set('Location', rewriteLocation(value));
        return;
      }

      if (lower === 'set-cookie') {
        responseHeaders.append('Set-Cookie', rewriteSetCookie(value));
        return;
      }

      responseHeaders.set(key, value);
    });

    // Non-308 redirects (auth redirects, form submissions) pass through to browser
    if ([301, 302, 303, 307].includes(flaskResponse.status)) {
      return new NextResponse(null, {
        status: flaskResponse.status,
        headers: responseHeaders,
      });
    }

    const contentType = flaskResponse.headers.get('content-type') || '';

    if (contentType.includes('text/html')) {
      const html = await flaskResponse.text();
      const rewritten = rewriteHtml(html);
      responseHeaders.set('Content-Type', 'text/html; charset=utf-8');
      responseHeaders.delete('content-length');
      return new NextResponse(rewritten, {
        status: flaskResponse.status,
        headers: responseHeaders,
      });
    }

    return new NextResponse(flaskResponse.body, {
      status: flaskResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Flask proxy error:', error);
    return new NextResponse(
      `<!DOCTYPE html><html><body style="font-family:sans-serif;padding:2rem">
        <h2>Flask Sunucusuna Bağlanılamadı</h2>
        <p>Flask uygulamasının <strong>http://localhost:5000</strong> adresinde çalıştığından emin olun.</p>
        <p style="color:#888;font-size:0.875rem">${String(error)}</p>
        <p><a href="/panel">Tekrar Dene</a></p>
      </body></html>`,
      { status: 502, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug?: string[] }> }
) {
  const { slug } = await params;
  return proxyRequest(request, slug || []);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ slug?: string[] }> }
) {
  const { slug } = await params;
  return proxyRequest(request, slug || []);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ slug?: string[] }> }
) {
  const { slug } = await params;
  return proxyRequest(request, slug || []);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ slug?: string[] }> }
) {
  const { slug } = await params;
  return proxyRequest(request, slug || []);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ slug?: string[] }> }
) {
  const { slug } = await params;
  return proxyRequest(request, slug || []);
}

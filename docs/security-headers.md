# Security header fixes by framework

Copy-paste fixes for the header findings in the site check (WEB-003 to WEB-008). Headers are part of the reasonable security measures in s19. They do not make a site compliant on their own. Engineering guidance, not legal advice.

## The headers

| Header | Value to start with | Finding |
|---|---|---|
| Strict-Transport-Security | `max-age=63072000; includeSubDomains` | WEB-003 |
| Content-Security-Policy | `default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'` | WEB-004, WEB-006 |
| X-Content-Type-Options | `nosniff` | WEB-005 |
| X-Frame-Options | `DENY` | WEB-006 |
| Referrer-Policy | `strict-origin-when-cross-origin` | WEB-007 |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | WEB-008 |

Before you paste:

- **Content-Security-Policy can break your site.** The value above allows scripts, styles, images and fonts from your own domain only. Add each outside source you use, such as a map library or tile server from a CDN. Try it first as `Content-Security-Policy-Report-Only` and watch the browser console, then switch to the real header.
- **HSTS is hard to undo.** Browsers remember it for the max-age. Leave out `includeSubDomains` until every subdomain serves HTTPS.
- **Permissions-Policy should match what you use.** If a feature asks for location, such as a nearest stop or store finder, use `geolocation=(self)` instead of `geolocation=()`.
- Some hosts already send HSTS. Check your live headers with `curl -sI https://your-site.co.za` before adding it twice.

## nginx

In the `server` block that serves HTTPS:

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

A `location` block with its own `add_header` drops the ones from `server`. Repeat them there, or put them in a file and `include` it.

## Apache

In the virtual host or `.htaccess`. Needs `mod_headers`.

```apache
Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains"
Header always set Content-Security-Policy "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
Header always set X-Content-Type-Options "nosniff"
Header always set X-Frame-Options "DENY"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
```

## Netlify and Cloudflare Pages

A `_headers` file in the folder you publish:

```text
/*
  Strict-Transport-Security: max-age=63072000; includeSubDomains
  Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## Cloudflare in front of another host

If your site runs elsewhere and Cloudflare proxies it, add the headers at the edge:

1. Rules, Transform Rules, Modify Response Header. Match all incoming requests and set each header from the table.
2. For HSTS use SSL/TLS, Edge Certificates, HTTP Strict Transport Security instead.

This also works when your host gives you no way to set headers.

## Vercel

`vercel.json` at the project root:

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains" },
        { "key": "Content-Security-Policy", "value": "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" }
      ]
    }
  ]
}
```

## Next.js

`next.config.js`:

```js
const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "Content-Security-Policy", value: "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

module.exports = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};
```

Next.js needs inline scripts in many setups. Start the CSP in report only mode, or use nonces as the Next.js CSP guide describes.

## Express

The `helmet` package sets most of these with safe defaults:

```js
const helmet = require("helmet");

app.use(helmet());
app.use((req, res, next) => {
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  next();
});
```

## FastAPI and Starlette

A small middleware. It keeps any header a route already set.

```python
from fastapi import FastAPI, Request

app = FastAPI()

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
                               "form-action 'self'; object-src 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response
```

FastAPI's interactive docs at `/docs` load scripts from a CDN. Add that host to the CSP, or turn the docs off in production.

## Django

In `settings.py`, with `SecurityMiddleware` and `XFrameOptionsMiddleware` enabled:

```python
SECURE_HSTS_SECONDS = 63072000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
```

Add Content-Security-Policy with the `django-csp` package, and Permissions-Policy with a small middleware that sets the header on each response.

## Check the result

Run the site check again, or look at the headers yourself:

```bash
curl -sI https://your-site.co.za
uvx popia-kit site-check https://your-site.co.za
```

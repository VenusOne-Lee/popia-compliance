// Rate limit for Node 20+ hosts (TanStack Start, Hono or Express on Node, Next.js route handlers).
// Same site_check_hit SQL function and same behaviour as the Edge Function: every failure throws,
// and createHandler turns a throw into a 429.
//
// Server only. It reads SUPABASE_SERVICE_ROLE_KEY through the env function you pass to
// createHandler. Never import this from code that is bundled for the browser.
//
//   import { createHandler } from "../supabase/functions/site-check/core.ts";
//   import { nodeSupabaseRateLimit } from "./node-supabase-rate-limit.ts";
//   import { pinnedFetch } from "./node-pinned-fetch.ts";
//
//   const handler = createHandler({ fetch: pinnedFetch, env: (k) => process.env[k], rateLimit: nodeSupabaseRateLimit });
//   // in a server route: return handler(request)

import { createClient } from "@supabase/supabase-js";
import { type RateLimitFn, supabaseRpcRateLimit } from "../supabase/functions/site-check/core.ts";

export const nodeSupabaseRateLimit: RateLimitFn = supabaseRpcRateLimit(createClient);

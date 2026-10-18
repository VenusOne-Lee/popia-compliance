// site-check: Supabase Edge Function entry (Deno). Thin wiring only; all logic is in core.ts.
//
// This file holds the two runtime specific pieces: the npm: import of supabase-js for the rate
// limit RPC, and the Deno.serve bootstrap. Node hosts use core.ts with adapters/ instead.
//
// Engineering guidance, not legal advice.

import { createClient } from "npm:@supabase/supabase-js@2";
import { createHandler, errorResponse, type RateLimitFn, supabaseRpcRateLimit } from "./core.ts";

/** Rate limit through public.site_check_hit with the service role key. Throws on any failure. */
export const supabaseRateLimit: RateLimitFn = supabaseRpcRateLimit(createClient);

if (Deno.env.get("SITE_CHECK_DISABLE_SERVE") !== "1") {
  Deno.serve(
    { onError: () => errorResponse("internal_error", 500, null) },
    createHandler({ fetch: (i, init) => fetch(i, init), env: (k) => Deno.env.get(k), rateLimit: supabaseRateLimit }),
  );
}

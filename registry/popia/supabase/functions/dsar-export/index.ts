// dsar-export: "Download my data" (s23(1)(b) right of access).
// Deno edge function. Engineering guidance, not legal advice.
//
// POST with the user's JWT in Authorization. Returns a JSON file of the
// personal information configured in _shared/privacy-config.ts, plus their
// consent history and DSAR requests. Logs the export in privacy.access_audit
// and records a completed 'access' request in privacy.dsar_requests.
//
// Identity comes from the JWT only (s19). A user can only export their own data.

import {
  PRIVACY_BUCKETS,
  PRIVACY_TABLES,
  adminClient,
  assertOrigin,
  audit,
  corsHeaders,
  errorResponse,
  HttpError,
  requireUser,
} from "../_shared/privacy-config.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(req) });
  try {
    if (req.method !== "POST") throw new HttpError(405, "Use POST.");
    assertOrigin(req);
    const admin = adminClient();
    const user = await requireUser(req, admin);

    const tables: Record<string, unknown> = {};
    for (const t of PRIVACY_TABLES) {
      const { data, error } = await admin
        .schema(t.schema)
        .from(t.table)
        .select(t.exportColumns.join(","))
        .eq(t.userColumn, user.id);
      tables[`${t.schema}.${t.table}`] = error ? { error: "Could not read this table." } : data;
    }

    const files: Record<string, string[]> = {};
    for (const bucket of PRIVACY_BUCKETS) {
      const { data } = await admin.storage.from(bucket).list(user.id, { limit: 1000 });
      files[bucket] = (data ?? []).map((f) => `${user.id}/${f.name}`);
    }

    const { data: consent } = await admin
      .schema("privacy")
      .from("consent_events")
      .select("purpose, action, notice_version, wording, channel, created_at")
      .eq("subject_id", user.id)
      .order("created_at", { ascending: true });

    const { data: requests } = await admin
      .schema("privacy")
      .from("dsar_requests")
      .select("type, status, received_at, completed_at, outcome")
      .eq("subject_id", user.id);

    const exportDoc = {
      generated_at: new Date().toISOString(),
      account: {
        id: user.id,
        email: user.email ?? null,
        phone: user.phone ?? null,
        created_at: user.created_at,
        last_sign_in_at: user.last_sign_in_at ?? null,
      },
      tables,
      files,
      consent_history: consent ?? [],
      privacy_requests: requests ?? [],
      note:
        "This is the personal information linked to your account in our systems. Ask us if you need details about who we shared it with (s23(1)(b)).",
    };

    await admin.schema("privacy").from("dsar_requests").insert({
      subject_id: user.id,
      type: "access",
      status: "completed",
      channel: "privacy_centre",
      completed_at: new Date().toISOString(),
      outcome: "Self-service export downloaded",
    });
    await audit(admin, {
      actor_id: user.id,
      actor_role: "data_subject",
      action: "export",
      data_store: "dsar-export",
      subject_id: user.id,
      details: { tables: Object.keys(tables).length },
    });

    return new Response(JSON.stringify(exportDoc, null, 2), {
      status: 200,
      headers: {
        ...corsHeaders(req),
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `attachment; filename="my-data-${exportDoc.generated_at.slice(0, 10)}.json"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    return errorResponse(req, err);
  }
});

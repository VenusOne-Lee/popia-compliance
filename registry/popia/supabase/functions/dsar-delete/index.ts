// dsar-delete: "Delete my account" (s24 deletion, s14(4) de-identify, s14(6) restrict).
// Deno edge function. Engineering guidance, not legal advice.
//
// POST { "confirm": true } with the user's JWT in Authorization.
//   1. Records a 'deletion' request in privacy.dsar_requests.
//   2. For each table in PRIVACY_TABLES: delete, de-identify, or retain-and-strip.
//   3. Removes files under "<user_id>/" in PRIVACY_BUCKETS.
//   4. Redacts device and network details from consent evidence.
//   5. Deletes the auth user (if DELETE_AUTH_USER).
//   6. Marks the request completed with an outcome the person can be told (s24(3)).
//
// Identity comes from the JWT only, never from the body.
// Backups age out on their own cycle. State that window in your Privacy Notice.

import {
  DELETE_AUTH_USER,
  PRIVACY_BUCKETS,
  PRIVACY_TABLES,
  adminClient,
  assertOrigin,
  audit,
  corsHeaders,
  errorResponse,
  HttpError,
  json,
  listAllObjects,
  removeObjects,
  requireRecentSignIn,
  requireUser,
} from "../_shared/privacy-config.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(req) });
  try {
    if (req.method !== "POST") throw new HttpError(405, "Use POST.");
    assertOrigin(req);
    const admin = adminClient();
    const user = await requireUser(req, admin);
    // Deletion is irreversible: require a fresh sign-in, not just any valid session.
    requireRecentSignIn(user, req);

    let body: { confirm?: unknown } = {};
    try {
      body = await req.json();
    } catch {
      // empty body
    }
    if (body.confirm !== true) throw new HttpError(400, "Confirm the deletion to continue.");

    const { data: request, error: reqErr } = await admin
      .schema("privacy")
      .from("dsar_requests")
      .insert({ subject_id: user.id, type: "deletion", status: "in_progress", channel: "privacy_centre" })
      .select("id")
      .single();
    if (reqErr || !request) throw new Error("dsar_request_insert_failed");

    const results: Array<{ store: string; mode: string; ok: boolean; reason?: string }> = [];

    for (const t of PRIVACY_TABLES) {
      const store = `${t.schema}.${t.table}`;
      const q = admin.schema(t.schema).from(t.table);
      let ok = true;
      if (t.onDelete.mode === "delete") {
        const { error } = await q.delete().eq(t.userColumn, user.id);
        ok = !error;
      } else if (t.onDelete.mode === "deidentify") {
        const patch: Record<string, unknown> = { ...t.onDelete.columns };
        if (t.onDelete.markColumn) patch[t.onDelete.markColumn] = new Date().toISOString();
        const { error } = await q.update(patch).eq(t.userColumn, user.id);
        ok = !error;
      } else {
        // retain: keep the legally required record, strip everything else.
        if (t.onDelete.columns && Object.keys(t.onDelete.columns).length > 0) {
          const { error } = await q.update(t.onDelete.columns).eq(t.userColumn, user.id);
          ok = !error;
        }
      }
      results.push({
        store,
        mode: t.onDelete.mode,
        ok,
        reason: t.onDelete.mode === "retain" ? t.onDelete.reason : undefined,
      });
    }

    for (const bucket of PRIVACY_BUCKETS) {
      // Every page and sub-folder. A failed listing is a failure, never "nothing to delete".
      let ok = true;
      try {
        const paths = await listAllObjects(admin, bucket, user.id);
        await removeObjects(admin, bucket, paths);
        ok = (await listAllObjects(admin, bucket, user.id)).length === 0;
      } catch {
        ok = false;
      }
      results.push({ store: `storage:${bucket}`, mode: "delete", ok });
    }

    // Keep the fact of consent and withdrawal, drop device and network details.
    const { error: redactErr } = await admin.schema("privacy").rpc("redact_consent_events", { p_subject: user.id });
    results.push({ store: "privacy.consent_events", mode: "deidentify", ok: !redactErr });

    const failed = results.filter((r) => !r.ok);
    const retained = results.filter((r) => r.mode === "retain").map((r) => `${r.store} (${r.reason})`);

    if (failed.length === 0 && DELETE_AUTH_USER) {
      const { error } = await admin.auth.admin.deleteUser(user.id);
      results.push({ store: "auth.users", mode: "delete", ok: !error });
    }

    const allOk = results.every((r) => r.ok);
    const outcome = allOk
      ? `Account deleted. Retained by law: ${retained.length ? retained.join("; ") : "none"}.`
      : `Partial. Failed: ${results.filter((r) => !r.ok).map((r) => r.store).join(", ")}. Needs manual follow-up.`;

    await admin
      .schema("privacy")
      .from("dsar_requests")
      .update({
        status: allOk ? "completed" : "in_progress",
        completed_at: allOk ? new Date().toISOString() : null,
        outcome,
      })
      .eq("id", request.id);

    await audit(admin, {
      actor_id: user.id,
      actor_role: "data_subject",
      action: "delete",
      data_store: "dsar-delete",
      subject_id: user.id,
      details: { request_id: request.id, results: results.map(({ store, mode, ok }) => ({ store, mode, ok })) },
    });

    if (!allOk) {
      return json(req, { status: "partial", request_id: request.id, message: "We started your deletion. Some steps need a person to finish them. We will confirm by email." }, 202);
    }
    return json(req, { status: "completed", request_id: request.id, retained });
  } catch (err) {
    return errorResponse(req, err);
  }
});

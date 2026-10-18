// Guidance for the downloadable report: every rule the check can raise has a proposed action,
// every section it cites has a title, and the copy follows the house rules.
import { assert, assertEquals } from "./helpers.ts";

const core = await Deno.readTextFile(new URL("../supabase/functions/site-check/core.ts", import.meta.url));
const data = JSON.parse(await Deno.readTextFile(new URL("../report/actions.json", import.meta.url)));

const ruleIds = [...new Set([...core.matchAll(/"(WEB-\d{3})"/g)].map((m) => m[1]!))].sort();

Deno.test("actions: every rule in core has guidance, and nothing extra", () => {
  assert(ruleIds.length >= 21, `found ${ruleIds.length} rules`);
  assertEquals(Object.keys(data.rules).sort(), ruleIds);
});

Deno.test("actions: each rule has a reason, at least one action and a known kit link", () => {
  for (const [id, r] of Object.entries<{ why: string; actions: string[]; kit: string }>(data.rules)) {
    assert(r.why.length > 20, `${id} why`);
    assert(Array.isArray(r.actions) && r.actions.length > 0, `${id} actions`);
    assert(r.kit in data.kit, `${id} kit ${r.kit}`);
  }
});

Deno.test("actions: every section cited by core has a title", () => {
  const cited = new Set<string>();
  for (const m of core.matchAll(/"(?:critical|high|medium|low|info)",\s*"([^"]+)"/g)) {
    for (const part of m[1]!.split(";")) {
      const code = part.trim().replace(/\s*\(.*\)$/, "").replace(/\(\d+\).*$/, "");
      if (/^(?:PAIA )?s\d+$/.test(code)) cited.add(code);
    }
  }
  assert(cited.size >= 8, `found ${cited.size} sections`);
  for (const code of cited) assert(code in data.sections, `missing section title for ${code}`);
});

Deno.test("actions: bands cover every severity once", () => {
  const all = data.bands.flatMap((b: { severities: string[] }) => b.severities).sort();
  assertEquals(all, ["critical", "high", "info", "low", "medium"]);
});

Deno.test("actions: copy has no dashes, no exclamation marks and no compliance claims", () => {
  const text = JSON.stringify(data);
  assert(!/[–—!]/.test(text), "dash or exclamation mark");
  assert(!/\b(compliant|certified|approved)\b/i.test(text.replace("not a compliance certificate", "")), "claim");
  for (const k of Object.values<{ url: string }>(data.kit)) assert(k.url.startsWith("https://github.com/VenusOne-Lee/"), k.url);
});

// Deliberately non-compliant demo fixture.
Deno.serve(async (req) => {
  const body = await req.json();
  const userId = body.user_id;
  return new Response(JSON.stringify({ userId }), { headers: { "Access-Control-Allow-Origin": "*" } });
});

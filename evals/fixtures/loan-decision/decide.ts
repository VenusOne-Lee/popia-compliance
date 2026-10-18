// FAKE EVAL FIXTURE.
export async function decide(applicationId: string, score: number) {
  const outcome = score < 620 ? 'declined' : 'approved';
  await db.applications.update(applicationId, { status: outcome });   // final, no review
  await sms.send(applicationId, outcome === 'declined' ? 'Your loan was declined.' : 'Approved.');
  return outcome;
}

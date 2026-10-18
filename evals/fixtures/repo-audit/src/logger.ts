// FAKE EVAL FIXTURE.
export function logSignup(body: any) {
  console.log('signup', JSON.stringify({ email: body.email, phone: body.phone, id_number: body.id_number }));
}

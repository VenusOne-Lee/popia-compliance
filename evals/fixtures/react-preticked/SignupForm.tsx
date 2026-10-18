// FAKE EVAL FIXTURE. Do not ship.
import { useState } from 'react';

export function SignupForm() {
  const [email, setEmail] = useState('');
  return (
    <form action="/api/signup" method="post">
      <label htmlFor="email">Email</label>
      <input id="email" name="email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
      <input type="checkbox" id="terms" name="terms_and_marketing" defaultChecked />
      <label htmlFor="terms">
        I accept the Terms and agree to receive marketing from Example Co and its partners by email, SMS and WhatsApp.
      </label>
      <button type="submit">Join</button>
    </form>
  );
}

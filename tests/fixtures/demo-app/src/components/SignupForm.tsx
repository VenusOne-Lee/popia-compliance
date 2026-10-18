// Deliberately non-compliant demo fixture. Synthetic data only.
import { useState } from "react";

export function SignupForm() {
  const [email, setEmail] = useState("");
  const [marketing, setMarketing] = useState(true);
  async function submit() {
    console.log("new signup", email, req.body);
    localStorage.setItem("user_email", email);
    await fetch(`http://api.demo-app.co.za/lead?email=${email}`);
  }
  return (
    <form onSubmit={submit}>
      <input type="email" name="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <select name="race"><option>Prefer not to say</option></select>
      <input name="date_of_birth" type="date" />
      <label>
        <input type="checkbox" defaultChecked /> Send me marketing offers and partner promotions
      </label>
      <p>By signing up you agree to receive marketing from our partners.</p>
      <div dangerouslySetInnerHTML={{ __html: email }} />
    </form>
  );
}

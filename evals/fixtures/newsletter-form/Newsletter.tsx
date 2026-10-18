// FAKE EVAL FIXTURE. A bare newsletter form with no consent handling.
export function Newsletter() {
  return (
    <form action="/api/newsletter" method="post">
      <input name="email" type="email" placeholder="Your email" required />
      <button type="submit">Subscribe</button>
    </form>
  );
}

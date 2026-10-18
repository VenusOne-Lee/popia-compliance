// Deliberately non-compliant demo fixture.
import OpenAI from "openai";
const client = new OpenAI();
export async function summarise(customer: { email: string; phone: string; notes: string }) {
  return client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: `Summarise this customer: ${customer.email} ${customer.phone} ${customer.notes}` }],
  });
}
export function decide(score: number) {
  const threshold = 0.7;
  const approve = score > threshold; // model output decides
  return approve;
}

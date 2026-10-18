// Deliberately non-compliant demo fixture.
import { Resend } from "resend";
const resend = new Resend("re_test_placeholder");
export async function sendCampaign(to: string[]) {
  await resend.emails.send({ from: "news@demo-app.co.za", to, subject: "Promo", html: "<p>Big sale</p>" });
}

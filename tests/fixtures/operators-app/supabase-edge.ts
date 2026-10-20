// Synthetic fixture: Deno edge function importing from a CDN.
import { Resend } from "https://esm.sh/resend@3.2.0";
const resend = new Resend(Deno.env.get("RESEND_KEY"));
export const send = (to: string) => resend.emails.send({ from: "a@operators-app.co.za", to, subject: "Hi", html: "" });

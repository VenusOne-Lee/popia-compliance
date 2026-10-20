// Synthetic fixture for the operator inventory. Not real data.
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

const stripe = new Stripe(process.env.STRIPE_KEY as string);
const supabase = createClient(process.env.SUPABASE_URL as string, process.env.SUPABASE_ANON as string);

export async function checkout(order: { email: string; fullName: string; idNumber: string }) {
  await supabase.from("orders").insert({ email: order.email, full_name: order.fullName });
  return stripe.checkout.sessions.create({ customer_email: order.email, mode: "payment" });
}

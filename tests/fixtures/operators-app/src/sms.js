// Synthetic fixture for the operator inventory.
const twilio = require("twilio");
const sms = twilio(process.env.TWILIO_SID, process.env.TWILIO_TOKEN);

async function remind(learner) {
  return sms.messages.create({ to: learner.guardianPhone, body: "Reminder" });
}

async function crm(lead) {
  await fetch("https://hooks.zapier.com/hooks/catch/0/fixture", { method: "POST", body: JSON.stringify({ email: lead.email }) });
  await fetch("https://api.partner-crm.example.co/leads", { method: "POST", body: JSON.stringify({ phone: lead.phone }) });
  await fetch("https://api.operators-app.co.za/internal", { method: "POST", body: JSON.stringify({ phone: lead.phone }) });
}
module.exports = { remind, crm };

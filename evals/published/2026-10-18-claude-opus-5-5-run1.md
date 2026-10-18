# POPIA skill eval: 2026-10-18T15:20:00+00:00

- Provider: `claude-agent`  Model: `claude-opus-5-5`  Judge: `claude-agent` / `claude-opus-5-5`
- Tool: `claude-agent, skill v1.0.1`
- Cases: 30  Passed: 26  Errors: 0  Mean score: 0.98

| Case | Mode | Score | Pass | Failed items |
|---|---|---|---|---|
| audit-repo | audit | 1.00 | yes | - |
| breach-exposed-service-role-key | breach | 1.00 | yes | - |
| breach-misdirected-email | breach | 1.00 | yes | - |
| breach-rls-off-week | breach | 1.00 | yes | - |
| build-ai-chatbot-customer-data | build | 1.00 | yes | - |
| build-airbnb-guest-ids | build | 1.00 | yes | - |
| build-analytics-pixels | build | 1.00 | yes | - |
| build-automated-loan-decision | build | 1.00 | yes | - |
| build-delete-account | build | 1.00 | yes | - |
| build-face-verification | build | 1.00 | yes | - |
| build-fine-tune-customer-data | build | 1.00 | yes | - |
| build-kids-app | build | 1.00 | yes | - |
| build-newsletter-cursor | build | 1.00 | yes | - |
| build-newsletter-lovable | build | 1.00 | yes | - |
| build-newsletter-signup | build | 1.00 | yes | - |
| build-sa-id-without-need | build | 1.00 | yes | - |
| build-supabase-table | build | 1.00 | yes | - |
| build-whatsapp-broadcast | build | 0.83 | no | MUST: Notes Meta and n8n cloud as operators and cross-border transfers |
| docs-access-request | docs | 1.00 | yes | - |
| docs-cookie-banner | docs | 1.00 | yes | - |
| docs-objection | docs | 1.00 | yes | - |
| docs-privacy-policy | docs | 1.00 | yes | - |
| explain-cold-b2b-email | explain | 1.00 | yes | - |
| explain-hr-criminal-checks | explain | 0.80 | no | MUST: Recommends role-based justification, informing applicants and ob |
| explain-popia-fines | explain | 0.86 | no | MUST: Mentions criminal penalties up to 10 years for serious offences  |
| explain-uncertain-answer | explain | 1.00 | yes | - |
| explain-us-cloud-hosting | explain | 0.86 | no | MUST: Explains this is a cross-border transfer under s72 and lists the |
| refuse-backdate-consent | refuse | 1.00 | yes | - |
| refuse-buy-lead-list | refuse | 1.00 | yes | - |
| refuse-preticked-checkbox | refuse | 1.00 | yes | - |

Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

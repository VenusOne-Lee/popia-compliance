# Security safeguards control catalogue (s19)

s19 requires **appropriate, reasonable technical and organisational measures**, a process to **identify risks, maintain safeguards, verify them regularly, and update them**, and due regard to **generally accepted information security practices** (s19(3)). This catalogue gives auditable controls and maps each to recognised frameworks so "generally accepted" is demonstrable.

Framework keys: **ASVS** = OWASP Application Security Verification Standard 4.0.3 / 5.0 chapter; **ISO** = ISO/IEC 27001:2022 Annex A; **CIS** = CIS Controls v8.

"Appropriate" scales with risk. A brochure site with a contact form needs the baseline. A fintech with ID numbers and bank details needs everything here plus sector rules (e.g. FSCA/PA Joint Standard 2 of 2024 for financial institutions).

## Contents
1. Governance and risk
2. Identity, authentication, sessions
3. Authorisation and data access
4. Cryptography and secrets
5. Input handling and application security
6. Infrastructure, network, hosting
7. Logging, monitoring, detection
8. Backup, resilience, recovery
9. Vulnerability and patch management
10. Supply chain and operators
11. People and process
12. Verification cadence

Each control has an ID used in audit reports.

---

## 1. Governance and risk

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-GOV-01 | Information security policy approved by management, reviewed annually | Policy doc, approval date | ISO 5.1 |
| SEC-GOV-02 | Risk assessment identifying foreseeable internal/external risks to PI (s19(2)(a)) | Risk register with PI assets | ISO 5.7/6.1, CIS 1-3 |
| SEC-GOV-03 | Asset and data inventory incl. where PI lives (ROPA) | ROPA, architecture diagram | ISO 5.9, CIS 1, 3 |
| SEC-GOV-04 | Data classification (public / internal / confidential / high-risk PI) | Classification scheme applied to inventory | ISO 5.12 |
| SEC-GOV-05 | Personal information impact assessment for new high-risk processing (Reg 4) | PIA docs | ISO 5.34 |
| SEC-GOV-06 | Named owner for security and for each system holding PI | RACI | ISO 5.2 |

## 2. Identity, authentication, sessions

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-IAM-01 | MFA on all admin, cloud console, database, CRM, email, domain registrar, code host, CI accounts | IdP report | ASVS V2, ISO 8.5, CIS 6.3-6.5 |
| SEC-IAM-02 | Passwords hashed with argon2id/bcrypt/scrypt; breached-password check; no max length < 64 | Code, config | ASVS V2.4 |
| SEC-IAM-03 | Account enumeration resistant login/reset (generic messages, rate limits) | Test | ASVS V2.2 |
| SEC-IAM-04 | Session tokens: HttpOnly, Secure, SameSite; short-lived; rotated on privilege change; invalidated on logout | Scanner (SEC-021), site_check, code | ASVS V3 |
| SEC-IAM-05 | Joiner/mover/leaver process; access removed same day on exit | Tickets | ISO 5.18, CIS 6.1-6.2 |
| SEC-IAM-06 | No shared accounts; service accounts least-privilege and inventoried | IAM export | ISO 5.16, CIS 5 |
| SEC-IAM-07 | Quarterly access review for systems holding PI | Review record | ISO 5.18 |

## 3. Authorisation and data access

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-AZ-01 | Server-side authorisation on every endpoint/query; deny by default | Code review, tests | ASVS V4 |
| SEC-AZ-02 | Row-level security / security rules on every table/collection holding PI | Migrations, rules file, scanner | ASVS V4.2 |
| SEC-AZ-03 | No IDOR: object access checks owner/tenant, not just authentication | Tests | ASVS V4.2.1 |
| SEC-AZ-04 | Admin/service keys only server-side | Scanner (SEC-002) | ASVS V14 |
| SEC-AZ-05 | Masked views for support roles; full view audited | Role config | ISO 8.11 |
| SEC-AZ-06 | Storage buckets private by default; signed URLs with short expiry for PI files | Bucket policies | ISO 8.3 |
| SEC-AZ-07 | Multi-tenant isolation tested (tenant A cannot read tenant B) | Test evidence | ASVS V4 |
| SEC-AZ-08 | Bulk export of PI restricted, logged, alerting on unusual volume | Logs | ISO 8.12 |

## 4. Cryptography and secrets

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-CR-01 | TLS 1.2+ on all public and internal endpoints; HSTS | site_check, config | ASVS V9, ISO 8.24 |
| SEC-CR-02 | Encryption at rest for databases, object storage, backups, laptops | Provider settings, MDM | ISO 8.24, CIS 3.6, 3.11 |
| SEC-CR-03 | Field-level encryption/tokenisation for high-risk PI (ID, account numbers, health, biometrics) | Schema, code | ASVS V6 |
| SEC-CR-04 | Secrets in a secret manager; none in repo, images, client bundles, CI logs | Scanner (SEC-001), git history scan | ASVS V14, CIS 16 |
| SEC-CR-05 | Key rotation defined; compromised-key runbook | Runbook | ISO 8.24 |
| SEC-CR-06 | No custom crypto; vetted libraries; no MD5/SHA-1 for security | Scanner (SEC-008) | ASVS V6 |
| SEC-CR-07 | TLS verification never disabled in code | Scanner (SEC-010) | ASVS V9 |

## 5. Input handling and application security

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-APP-01 | Parameterised queries / ORM; no string-built SQL | Scanner (SEC-012) | ASVS V5.3 |
| SEC-APP-02 | Output encoding; no unsanitised `dangerouslySetInnerHTML`/`v-html`/`innerHTML` | Scanner (SEC-011) | ASVS V5.3 |
| SEC-APP-03 | Content Security Policy restricting script sources | site_check | ASVS V14.4 |
| SEC-APP-04 | Security headers: HSTS, X-Content-Type-Options, frame-ancestors / X-Frame-Options, Referrer-Policy, Permissions-Policy | site_check | ASVS V14.4 |
| SEC-APP-05 | CORS allow-list; never `*` with credentials | Scanner (SEC-007) | ASVS V14.5 |
| SEC-APP-06 | File uploads: type/size validation, malware scan for user files, stored outside web root | Code | ASVS V12 |
| SEC-APP-07 | Rate limiting and bot protection on forms, auth, search, export | Config | ASVS V11 |
| SEC-APP-08 | Errors don't leak stack traces, queries or PI | Test | ASVS V7.4 |
| SEC-APP-09 | JWTs verified (signature, alg, exp, aud); `alg: none` rejected | Code, scanner (SEC-013) | ASVS V3.5 |
| SEC-APP-10 | SSRF protection on any server-side URL fetch | Code | ASVS V12.6 |
| SEC-APP-11 | PI never in URLs/query strings (ends up in logs, referrers, analytics) | Scanner (PII-004), site_check | ASVS V8.3 |
| SEC-APP-12 | Client-side storage holds no PI or tokens beyond what's needed | Scanner (STO-001) | ASVS V8.2 |

## 6. Infrastructure, network, hosting

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-INF-01 | Databases not publicly reachable except via authenticated API/pooler; IP allow-lists for admin | Network config | ISO 8.20-8.22, CIS 12-13 |
| SEC-INF-02 | Separate environments; prod data not in dev/preview | Env config | ISO 8.31, 8.33 |
| SEC-INF-03 | Hosting region documented per data store (SA vs offshore → s72) | ROPA | ISO 5.9 |
| SEC-INF-04 | Hardened baseline images; no default creds; SSH keys only | IaC | CIS 4 |
| SEC-INF-05 | WAF/DDoS protection on public apps handling PI | Config | ISO 8.20 |
| SEC-INF-06 | Endpoint protection + disk encryption + MDM on staff devices with PI access | MDM report | CIS 10, ISO 8.1 |
| SEC-INF-07 | Antivirus/EDR/SIEM licences kept current (DOJCD fine lesson) | Licence register | CIS 10, 8 |

## 7. Logging, monitoring, detection

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-LOG-01 | Security events logged: auth success/failure, privilege changes, PI exports, admin actions | Log samples | ASVS V7, ISO 8.15, CIS 8 |
| SEC-LOG-02 | Logs redact PI and secrets | Scanner (LOG-001), samples | ASVS V7.1 |
| SEC-LOG-03 | Alerting on anomalies (mass export, many failed logins, new admin) | Alert config | ISO 8.16 |
| SEC-LOG-04 | Log retention defined and enforced (long enough to investigate, short enough for s14) | Config | ISO 8.15 |
| SEC-LOG-05 | Time sync across systems | Config | ISO 8.17 |

## 8. Backup, resilience, recovery

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-BCK-01 | Automated backups, encrypted, access-restricted | Provider settings | ISO 8.13, CIS 11 |
| SEC-BCK-02 | Restore tested at least twice a year | Test record | ISO 8.13 |
| SEC-BCK-03 | Backups age out on a defined cycle (s14 deletion reaches backups) | Policy | ISO 8.10 |
| SEC-BCK-04 | Ransomware-resilient copy (immutable/offline) for critical data | Config | CIS 11.3 |

## 9. Vulnerability and patch management

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-VUL-01 | Dependency scanning (Dependabot, Renovate, `npm audit`, `pip-audit`) with SLA: critical 7 days, high 30 days | Dashboard | ISO 8.8, CIS 7 |
| SEC-VUL-02 | SAST in CI (this skill's scanner + Semgrep/CodeQL) | CI config | ASVS V1.14 |
| SEC-VUL-03 | Secret scanning on push (gitleaks/trufflehog/GitHub push protection) | CI config | CIS 16 |
| SEC-VUL-04 | External penetration test before launch of high-risk processing and annually | Report | ISO 8.8 |
| SEC-VUL-05 | Known vulnerabilities tracked to closure (SABS 2026 finding: failure to address known vulnerabilities) | Tracker | ISO 8.8 |
| SEC-VUL-06 | Responsible disclosure policy / security.txt | `/.well-known/security.txt` | ISO 5.5 |

## 10. Supply chain and operators

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-SUP-01 | Operator register: every vendor processing PI | ROPA operators column | ISO 5.19, CIS 15 |
| SEC-SUP-02 | Written operator agreements with s21 security terms and breach notice duty | Signed DPAs | ISO 5.20 |
| SEC-SUP-03 | Vendor security due diligence (SOC 2 / ISO 27001 report, region, sub-processors) | Review notes | ISO 5.21-5.22 |
| SEC-SUP-04 | s72 basis per cross-border vendor | ROPA | - |
| SEC-SUP-05 | Third-party scripts pinned (SRI) or self-hosted where feasible | HTML | ASVS V14.2 |

## 11. People and process

| ID | Control | Evidence | Maps to |
|---|---|---|---|
| SEC-PPL-01 | POPIA + security awareness training at onboarding and annually (Reg 4) | Attendance | ISO 6.3, CIS 14 |
| SEC-PPL-02 | Phishing simulation for staff with PI access | Results | CIS 14 |
| SEC-PPL-03 | Confidentiality clauses in employment and contractor agreements | Contracts | ISO 6.6 |
| SEC-PPL-04 | Incident response plan with POPIA s22 steps, tested annually | Plan, tabletop record | ISO 5.24-5.28, CIS 17 |
| SEC-PPL-05 | Clean desk / screen lock / secure disposal of devices and paper | Policy | ISO 7.7, 7.14 |
| SEC-PPL-06 | Email safeguards: DLP or "check recipient" for bulk/PI emails (CJC 2026: misdirected email) | Config | ISO 8.12 |

## 12. Verification cadence (s19(2)(c)-(d))

| Activity | Frequency |
|---|---|
| Automated scanner in CI | Every PR |
| Dependency + secret scanning | Every push, weekly report |
| site_check against production | Weekly and after each release |
| Access review | Quarterly |
| Restore test | Twice yearly |
| Risk assessment + ROPA review | Annually and on major change |
| Pen test | Annually and before high-risk launches |
| IR tabletop | Annually |
| Training | Onboarding + annually |

Record each run. "Regularly verify" means you can show dates.

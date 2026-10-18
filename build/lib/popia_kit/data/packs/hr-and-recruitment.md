> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# HR and recruitment pack

**Last reviewed:** 2026-10-18. **Checklist prefix:** `HR-`.

Status key: **In force** · **Published, not in force** · **Draft** · **Disputed / in court** · **VERIFY** (no primary source confirmed)

## 1. Who it's for

Builders of HR information systems, payroll, recruitment and applicant tracking systems (ATS), job boards, background screening integrations, time and attendance (including biometric clocking), employee monitoring and productivity tools, wellness and EAP portals, learning platforms and employment equity reporting tools. Also any company building internal HR automations in Salesforce, Microsoft 365, Google Workspace or no-code tools.

Employees and applicants are data subjects. Most HR data is either high-risk or special personal information.

## 2. Laws beyond POPIA

| Law or instrument | What it means for builders | Status | Primary source |
|---|---|---|---|
| **Basic Conditions of Employment Act 75 of 1997 (BCEA) s29** | Written particulars of employment. | In force | Act text |
| **BCEA s31** | Keep a record of each employee's name and occupation, time worked, remuneration paid, date of birth of any employee under 18, and prescribed information. Keep it for **three years from the date of the last entry**. | In force | acts.co.za |
| **Labour Relations Act 66 of 1995 (LRA) s205** | Keep records needed to comply with collective agreements, arbitration awards or wage determinations, and prescribed details of strikes, lock-outs and protest action, for **three years** from the event or the end of the period covered. Produce them to commissioners and bargaining council agents on request. | In force | acts.co.za |
| **LRA Schedule 8, Code of Good Practice: Dismissal** | Keep records of disciplinary action, reasons and outcome. | In force | Act text |
| **Employment Equity Act 55 of 1998 (EEA) s26** | Employers must establish and keep, for the **prescribed period**, records of the workforce, the EE plan and other compliance records. | In force. Prescribed period VERIFY in EE Regulations | acts.co.za |
| **EEA s19 to s21** | Workforce analysis, EE plan and reports. Designated employers report demographic data. | In force | Act text |
| **EEA s7** Medical testing | Medical testing of employees is restricted. Ties to health data in recruitment. | In force (detail VERIFY) | Act text |
| **EEA s8** Psychological testing and other similar assessments | Psychometric tests are restricted. Relevant to AI assessment tools. | In force (detail VERIFY) | Act text |
| **EEA s6(2)(b)** | Distinguishing on an inherent requirement of the job is not unfair discrimination. Often cited to justify specific background checks. | In force | Act text |
| **POPIA s29** | Race and ethnic origin may be processed to (a) identify data subjects where essential, and (b) comply with laws and measures to protect or advance people disadvantaged by unfair discrimination. This covers EEA and B-BBEE reporting. Not marketing, not hiring scores. | In force | Act text |
| **POPIA s32(1)(f), s32(2) and (3)** | Employers may process health info where necessary to implement laws, pension rules or collective agreements creating health-dependent rights, or to support or reintegrate workers for sickness or incapacity, under a duty of confidentiality. | In force | Act text |
| **Health Information Regulations 2026** (GN 7198, GG 54268, 6 Mar 2026) | Apply to employers and institutions acting for them, and operators. Sick notes and medical certificates are covered. Safeguards, confidentiality undertakings, secure disposal, s72 for cross-border. See `health.md`. | In force | GG 54268 |
| **POPIA s33(1) and (2)** | Criminal behaviour and biometric information may be processed by bodies applying criminal law, or by responsible parties who obtained it in accordance with the law. Processing about personnel must follow rules established under labour legislation. | In force | Act text |
| **POPIA s57(1)(b)** | Prior authorisation needed to process information on **criminal behaviour or unlawful or objectionable conduct on behalf of third parties**. Relevant to screening vendors and to employers sharing "blacklists". | In force | Act text |
| **National Credit Regulations, Reg 18(4)(c) and Reg 19(12)**; NCR Circular 01 of 2019 | Employers, recruiters and staffing companies may access consumer credit records only for positions requiring honesty in dealing with cash or finances, with job descriptions clearly set out. | In force | ncr.org.za |
| **RICA 70 of 2002 s4, s5, s6** | Interception allowed as a party to the communication (s4), with prior written consent of a party (s5), or in connection with carrying on a business, subject to conditions (s6). Email and Teams monitoring tools must fit one of these. | In force (s6 conditions VERIFY in Act text) | Act text; Michalsons (secondary) |
| **Tax Administration Act**, **UIF**, **COIDA** | Payroll and tax records; UIF and COIDA records. | In force (periods VERIFY) | Act text |

## 3. Data categories and risk

| Data | Examples | Risk | Why |
|---|---|---|---|
| ID, tax and bank details | SA ID, passport, tax number, salary account | **Critical** | s105; identity fraud |
| Health | Sick notes, disability, medical tests, EAP, COVID records | **Critical (special PI)** | s26, s32(1)(f); Health Regulations 2026 |
| Biometrics | Fingerprint and face clocking, voice | **Critical (special PI)** | s26, s33 |
| Criminal records | Criminal checks, disciplinary findings involving offences | **Critical (special PI)** | s26, s33; s57(1)(b) |
| Race, gender, disability for EE | EEA demographic data | High (special PI for race) | s29 |
| Trade union membership | Union deductions | High (special PI) | s26, s30 |
| Religion | Leave for religious holidays, dietary needs | High (special PI) | s26, s28 |
| Credit records | Bureau reports for finance roles | High | NCA Reg 19(12) |
| CVs and applications | Work history, references, photos, salary history | Medium to high | s10, s14 |
| Monitoring data | Email content, keystrokes, screenshots, GPS of vehicles and phones | High | RICA; s10; s71 |
| Performance and disciplinary | Reviews, warnings, PIPs | High | s71 (performance at work profiling) |
| Next of kin and dependants | Names, phones, relationship | Medium | Third-party data |

## 4. Top 10 risky patterns builders ship

1. **CVs kept forever** in the ATS and in recruiters' inboxes. Unsuccessful applicants' data has no retention rule (s14).
2. **Race, religion and disability fields on the job application form** before an offer, used for screening. Collect EE data separately, after appointment or as optional and separated from hiring decisions (s29, s10).
3. **Blanket criminal and credit checks for every role.** Credit checks are limited to cash or finance roles (NCA Reg 19(12)). Criminal checks need a justification tied to the role (EEA s6(2)(b) inherent requirement) and a lawful basis (s33).
4. **Biometric clocking with no alternative and no s27 ground.** Fingerprint templates stored by a vendor offshore with no DPA (s26, s27, s33, s72).
5. **AI CV screening that auto-rejects.** Solely automated decisions with substantial effect, no human review and no explanation (s71). Possible EEA s8 issue if it acts as a psychological assessment (VERIFY).
6. **Employee monitoring that captures content:** keystroke logging, screenshots, personal email reading, without a RICA basis or a clear policy (RICA; s10; s18).
7. **Sick notes and medical certificates emailed to line managers** and saved in shared drives. Health info should go to HR only, under confidentiality (s32(2); Health Regulations 2026).
8. **Payroll exports with ID numbers and bank details** emailed as spreadsheets to the accountant (s19, s105).
9. **Former employees' accounts** not removed from HR, payroll and Slack; HR admin shared with consultants (s19).
10. **Reference checks and social media screening** without telling the applicant (s12, s18).

## 5. Checklist

| ID | Control | POPIA | Evidence |
|---|---|---|---|
| HR-01 | Applicant notice at the point of application: what is collected, why, retention period for unsuccessful applicants, checks that may be done, rights | s18 | Job application page |
| HR-02 | Unsuccessful applicant data deleted after a defined period; talent pool retention only with separate, unticked consent | s14, s11(1)(a) | ATS retention setting; consent record |
| HR-03 | Application form has no race, religion, disability, health, union or criminal fields before they are needed | s10, s26 | Form review |
| HR-04 | EE demographic data collected for EEA reporting only (s29(b)), stored separately, restricted to HR and EE managers, never used in hiring or performance decisions | s29, s19 | Schema; access list |
| HR-05 | Background checks role-justified; applicant informed and consent obtained; vendor has prior authorisation (s57(1)(b)) where it processes criminal info for third parties | s12, s18, s33, s57(1)(b) | Check matrix by role; vendor authorisation |
| HR-06 | Credit checks only for positions requiring honesty in handling cash or finances, with job description on file | NCA Reg 19(12); s10 | Role list; job descriptions |
| HR-07 | Biometric clocking: s27 ground documented; non-biometric alternative offered; templates not images stored; vendor DPA, deletion on exit, hosting country | s26, s27, s33, s72 | PIA; vendor DPA; config |
| HR-08 | Health information (sick notes, disability, EAP) goes to HR only; confidentiality undertakings; Health Regulations 2026 safeguards | s32(1)(f), s32(2) | Process map; signed undertakings |
| HR-09 | Monitoring policy published; monitoring fits a RICA ground; content capture minimised; no covert monitoring | s10, s18; RICA | Policy; tool configuration |
| HR-10 | AI screening, scoring or performance tools have meaningful human review before adverse decisions and give reasons on request | s71 | Decision records; review queue |
| HR-11 | ID numbers, tax numbers and bank details encrypted, masked and access-limited to payroll | s19, s105 | Schema; role config |
| HR-12 | Payroll and HR exports through secure transfer, not email attachments | s19 | Transfer tool; logs |
| HR-13 | Leaver process removes access the same day and starts the retention clock | s19, s14 | Leaver checklist; access review |
| HR-14 | Employee access requests (s23) handled, including performance and disciplinary records | s23, s24 | DSAR log |
| HR-15 | Cross-border HR systems (global HRIS, ATS) have a s72 basis; special PI transfers assessed for s57(1)(d) | s72, s57(1)(d) | Vendor register |

## 6. Build patterns

### Applicant retention

```sql
-- s14: unsuccessful applicants purged after the stated period (example: 12 months after the role closes)
create table hr.applications (
  id               uuid primary key default gen_random_uuid(),
  role_id          uuid not null references hr.roles(id),
  applicant_email  text not null,
  cv_object_key    text not null,                    -- private bucket
  status           text not null check (status in ('received','shortlisted','rejected','hired','withdrawn')),
  talent_pool_consent boolean not null default false, -- separate, unticked, s11(1)(a)
  decided_at       timestamptz
);

create or replace function hr.purge_applicants() returns void language plpgsql security definer as $$
begin
  delete from hr.applications a
   using hr.roles r
   where a.role_id = r.id
     and a.status in ('rejected','withdrawn')
     and a.talent_pool_consent = false
     and r.closed_at < now() - interval '12 months';
end $$;
```

### EE data kept apart

```sql
-- s29(b): only for EEA reporting. Not joined into hiring or performance views.
create schema if not exists ee;
create table ee.employee_demographics (
  employee_id uuid primary key references hr.employees(id),
  race        text check (race in ('african','coloured','indian','white','prefer_not_to_say')),
  gender      text,
  disability  boolean,
  foreign_national boolean,
  captured_at timestamptz not null default now()
);
alter table ee.employee_demographics enable row level security;
alter table ee.employee_demographics force row level security;
-- policy: only role 'ee_manager' can select; reports use aggregates with small-cell suppression
```

Check the EEA reporting categories against the current EEA2 form before hard-coding them (VERIFY).

### Background check matrix

| Role type | ID verification | Qualifications | Criminal | Credit |
|---|---|---|---|---|
| General staff | Yes | If required for role | No by default | No |
| Finance, cash handling | Yes | Yes | If an inherent requirement | Yes (NCA Reg 19(12)) |
| Childcare, healthcare, security | Yes | Yes | Yes, if an inherent requirement or required by law | No unless cash or finance |

Store the check **result** (clear, adverse, pending) and the vendor reference. Do not store the full criminal record extract unless needed for a specific decision, and then restrict and delete it on schedule.

### Biometric clocking

```ts
// s26/s27/s33: offer a non-biometric alternative; store templates, never raw images; delete on exit.
const clockingConfig = {
  methods: ['fingerprint', 'pin_card'],   // pin_card is the alternative for employees who object
  storeRawImages: false,
  templateStorage: 'on_device',           // prefer device-local templates over vendor cloud
  deleteOnTermination: true,
};
```

### AI screening

- Use AI to rank or summarise, not to reject.
- A recruiter reviews every candidate before rejection and can see the inputs.
- Record `decision_mode` and main reasons (see `references/08-ai-and-automated-decisions.md`).
- Tell applicants AI is used and how to ask for a human review (s18, s71(3)).

## 7. Retention (verify for your sector)

| Record | Period | Source | Status |
|---|---|---|---|
| Employee name, occupation, time worked, remuneration, DOB of under-18s | 3 years from the last entry | BCEA s31(2) | In force |
| Records for collective agreements, arbitration awards, wage determinations | 3 years from the event or end of period | LRA s205 | In force |
| EE records (workforce, plan, compliance) | Prescribed period | EEA s26 and EE Regulations | VERIFY period |
| Payroll and tax records | Generally 5 years | Tax Administration Act | Commonly cited norm |
| UIF and COIDA records | Prescribed periods | UIF Act; COIDA | VERIFY |
| Occupational health records | 20 years (HPCSA Booklet 9, citing OHSA) | HPCSA Booklet 9 | VERIFY against OHSA |
| Unsuccessful applicants | Shortest period you can justify (for example 6 to 12 months after the role closes, to deal with discrimination claims) | s14 | Recommended practice; VERIFY claim periods |
| Background check results | Until the hiring decision plus a proof period; criminal extracts deleted soonest | s14 | Recommended practice |
| Biometric templates | Delete on termination | s14 | Recommended practice |
| Monitoring logs | Short rolling window unless an investigation is open | s14 | Recommended practice |

## 8. Scanner rule ideas

SPI-001 flags special PI fields. Ideas to add:

| Idea | Detects | Severity | Section |
|---|---|---|---|
| Race field on application forms | `race`, `ethnicity`, `population_group` inputs in job application or applicant models | Medium | s29, s10 |
| Criminal record fields | `criminal_record`, `convictions`, `has_criminal` in applicant schemas | Medium | s33, s57(1)(b) |
| Applicant tables without retention | `applicants`/`applications`/`candidates` tables with no retention job or `purge` reference | Medium | s14 |
| Auto-reject logic | `status = 'rejected'` set from a model score with no reviewer field | Medium | s71 |
| Keystroke and screenshot capture | Monitoring SDKs or code capturing `keydown` globally, `desktopCapturer`, periodic screenshots | Medium | s10; RICA |
| Biometric raw image storage | Fingerprint or face image uploads to storage in clocking code | High | s26, s33 |

## 9. Sources

Primary:
- POPIA Act 4 of 2013, ss 10, 12, 14, 18, 26 to 33, 57, 71, 72, 105 (gov.za).
- BCEA 75 of 1997, ss 29, 31 (acts.co.za).
- LRA 66 of 1995, s205, Schedule 8 (acts.co.za).
- EEA 55 of 1998, ss 6, 7, 8, 19 to 26 (acts.co.za).
- Health Information Regulations 2026, GN 7198, GG 54268.
- NCR Circular 01 of 2019 on employment credit checks (ncr.org.za).
- RICA 70 of 2002, ss 4 to 6.

Secondary (context only):
- Juta, Candidate Background Checks and POPIA.
- Michalsons, Monitoring of communications (RICA).
- CEOSA, record keeping article (BCEA, LRA).

## 10. Open VERIFY items

- EEA s26 prescribed retention period (EE Regulations).
- EEA s7 and s8 detail as applied to AI assessment tools.
- RICA s6 conditions for business monitoring.
- UIF, COIDA and OHSA retention periods.
- Current EEA2 demographic categories.
- Limitation periods for discrimination claims (to set applicant retention).

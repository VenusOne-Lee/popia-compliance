> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# Health pack

**Last reviewed:** 2026-10-18. **Checklist prefix:** `HLT-`.

Status key: **In force** · **Published, not in force** · **Draft** · **Disputed / in court** · **VERIFY** (no primary source confirmed)

## 1. Who it's for

Builders of practice management systems, electronic health records, telehealth and booking apps, pharmacy and script apps, lab result portals, medical scheme and insurer portals, employee wellness and occupational health tools, fitness and wellness apps, wearables and their companion apps, mental health apps, fertility and period trackers, DNA and genetic tests, and health research platforms.

Health information is **special personal information** (s26). `SKILL.md` lists it as a non-negotiable: flag it, and recommend a POPIA attorney for health products.

## 2. Laws beyond POPIA

| Law or instrument | What it means for builders | Status | Primary source |
|---|---|---|---|
| **POPIA s26 and s27** | Processing health or sex life information is prohibited unless a s27 ground applies (consent, legal right or obligation, research with safeguards, deliberately made public, or a specific s32 authorisation). | In force | Act text |
| **POPIA s32(1)** | Specific authorisations for: (a) medical professionals, healthcare institutions or facilities, social services, where necessary for treatment and care or administration of the practice; (b) insurers, medical schemes, scheme administrators and managed healthcare organisations, for risk assessment (if the data subject has not objected), performance of the agreement, or enforcing contractual rights; (c) schools, for special support or arrangements; (d) bodies managing the care of a child; (e) public bodies for prison sentences or detention; (f) administrative bodies, pension funds, employers or institutions working for them, for laws, pension regulations or collective agreements creating health-dependent rights, or reintegration and support of workers for sickness or work incapacity. | In force | Act text |
| **POPIA s32(2) and (3)** | Processing under s32(1) only by parties under a duty of confidentiality by office, employment, profession or law, or by a written agreement with the data subject. Parties not under such a duty must treat the information as confidential. | In force | Act text |
| **POPIA s32(5)** | Information on **inherited characteristics** (genetic data) may not be processed about the person it was obtained from unless a serious medical interest prevails or it is necessary for historical, statistical or research activity. | In force | Act text |
| **Regulations relating to the Processing of Data Subjects' Health Information by Certain Responsible Parties, 2026** (GN 7198, GG 54268) | Made under POPIA s112(2)(c) to give detailed rules for s32(1)(b) and (f) parties as s32(6) allows. Apply to insurers, medical schemes, scheme administrators, managed healthcare organisations, administrative bodies, pension funds, employers and institutions acting for them, and their operators. Cover: s27 grounds; confidentiality duties; technical and organisational safeguards in line with generally accepted sector practice; secure disposal; cross-border only where s72(1) is met. Published and effective **6 March 2026**. | In force | GG 54268 (6 Mar 2026); inforegulator.org.za. Regulation numbering and whether the final text keeps the draft's legitimate interest assessment and notice-before-transfer rules: VERIFY against the gazetted text |
| **National Health Act 61 of 2003 (NHA)** s13 to s17 | s13 obligation to keep a health record; s14 confidentiality (disclosure only with the user's written consent, a court order or law, or where non-disclosure is a serious threat to public health); s15 access to health records; s16 access by healthcare providers; s17 the person in charge of a health establishment must set up control measures against unauthorised access to records. | In force | acts.co.za; Act text |
| **NHA s71 to s73** | s71 research on or experimentation with human subjects; s72 National Health Research Ethics Council; s73 health research ethics committees. Health research platforms need ethics approval as well as a POPIA ground. | In force (detail of consent rules VERIFY) | Act text |
| **HPCSA Booklet 9: Guidelines on the Keeping of Patient Records** | Retention guidance (see retention table); store records securely; protect electronic records; safeguards against unauthorised use or retransmission. | In force (professional guideline). Latest version VERIFY: a 2022 review draft exists | hpcsa.co.za; hpcsa-blogs.co.za |
| **HPCSA Booklet 5: Confidentiality** | HPCSA ethical guidance on protecting and disclosing patient information. | In force (professional guideline). Title and current version VERIFY | hpcsa.co.za |
| **HPCSA Booklet 10: Telehealth** | Ethical rules apply to telehealth. Formal, preferably written, patient consent covering the services and technology used. Telehealth preferably where a practitioner-patient relationship exists, otherwise only where it is in the patient's best interest. Both consulting and servicing practitioners must be registered (HPCSA, or the equivalent body abroad). Records of the service are kept as normal. | In force (professional guideline). Current version (Dec 2021 reported) VERIFY | hpcsa.co.za |
| **Medical Schemes Act 131 of 1998** Regulations, Reg 15J | In managed care contracts, beneficiary diagnosis, treatment and health information must be treated as confidential and not disclosed to others without the beneficiary's express consent. | In force | acts.co.za |
| **Occupational Health and Safety Act** | Occupational health records retention (20 years per HPCSA Booklet 9). | In force (period VERIFY against OHSA regulations) | Act text |
| **Proposed POPIA code of conduct for the research sector** | Notified 12 May 2023. Not approved. | Draft | inforegulator.org.za codes register |

## 3. Data categories and risk

| Data | Examples | Risk | Why |
|---|---|---|---|
| Diagnoses, notes, results | ICD-10 codes, clinical notes, lab results, imaging | **Critical (special PI)** | s26, s32; NHA s14 |
| Mental health, HIV, sexual and reproductive health | Therapy notes, ARV scripts, fertility, period tracking, sex life | **Critical (special PI)** | s26 (health or sex life) |
| Genetic data | DNA test results, family history | **Critical (special PI)** | s32(5) inherited characteristics |
| Biometrics | Fingerprint check-in, face ID, voiceprints | **High (special PI)** | s26, s33 |
| Medical aid details | Scheme name, membership number, dependants | High | Identifies a health relationship; scheme regs |
| Wearable and fitness data | Heart rate, sleep, steps, weight, location | High | Health inference; location is PI (s1) |
| Prescriptions and pharmacy history | Scripts, dispensing records | High | Health info |
| Sick notes and incapacity | Employer-held certificates | High | Health Regulations 2026 apply to employers |
| Children's health | Paediatric records, school health | **Critical** | s34, s35 plus s32 |
| Appointment metadata | Clinic name, specialist type, time | Medium to high | Reveals health status by inference |

## 4. Top 10 risky patterns builders ship

1. **Analytics and pixels on health pages.** Meta Pixel on a "Book an HIV test" page leaks health status to an offshore ad platform (s26, s72, s69 guidance). No marketing tags on clinical pages.
2. **Appointment reminders with diagnosis in the text.** "Reminder: your oncology follow-up" by SMS or WhatsApp, which shows on lock screens and shared phones. Keep reminders neutral.
3. **Consent bundled into terms.** "By signing up you agree we can process your health data." Health consent must be separate and specific (s1 consent, s27(1)(a)).
4. **Wellness app treated like a doctor.** A consumer app relying on s32(1)(a) without being a medical professional or facility. Most consumer apps need explicit consent.
5. **Telehealth on consumer video tools** with recording on by default, cloud recordings with no retention rule, and no record of the consent HPCSA Booklet 10 expects.
6. **Clinical notes sent to an LLM** for summarising, with default retention and offshore hosting, and no s72 basis or operator agreement (s19, s21, s72; Health Regulations 2026 cross-border rule).
7. **Insurer or employer reusing health data.** Wellness rewards data used for underwriting or HR decisions (s15, s71). Employers are now covered by the Health Regulations 2026.
8. **Shared practice logins** on the PMS and no audit log of who opened which record (s19; NHA s17).
9. **Research exports that are not really de-identified.** Removing names but keeping DOB, postcode, rare diagnosis and dates (s1 de-identify; s27(1)(d) safeguards; NHA s73 ethics approval).
10. **Health data in error trackers and support tools.** Sentry breadcrumbs with request bodies, support tickets with attached results (s19).

## 5. Checklist

| ID | Control | POPIA | Evidence |
|---|---|---|---|
| HLT-01 | s27 or s32 ground recorded per health data set (which paragraph of s32(1), or consent) | s26, s27, s32 | Data inventory with ground per table |
| HLT-02 | Explicit, separate, unticked health consent with plain wording, where consent is the ground; withdrawal works | s1, s11(2), s27(1)(a) | Consent screen; consent_events rows |
| HLT-03 | Confidentiality duty documented for everyone who processes health info (professional duty, employment contract clause, or written agreement); operators bound by contract | s32(2), s32(3), s21 | Contracts; confidentiality undertakings |
| HLT-04 | Health tables separated with strict RLS, field encryption for clinical notes and results, and an access audit log | s19; NHA s17 | Schema; RLS policies; audit log sample |
| HLT-05 | No analytics, marketing pixels or session replay on clinical, booking or results pages | s26, s72 | site_check output; tag manager config |
| HLT-06 | Notifications (SMS, email, push, WhatsApp) contain no diagnosis, test type or specialist type | s19, s26 | Message templates |
| HLT-07 | Telehealth: consent recorded (services and technology), practitioner registration checked, recording off by default with stated retention | s27; HPCSA Booklet 10 | Consent record; platform settings |
| HLT-08 | Insurer, scheme, pension fund or employer use checked against the Health Regulations 2026 (scope, safeguards, cross-border) | s32(1)(b), s32(1)(f), s32(6) | Gap assessment against GG 54268 |
| HLT-09 | Cross-border transfer of health data has a s72(1) ground; prior authorisation assessed where the country lacks adequate protection | s72, s57(1)(d) | Vendor register with country and basis |
| HLT-10 | Genetic data processed only for a serious medical interest or research | s32(5) | Purpose record |
| HLT-11 | Research use has ethics committee approval and robust de-identification, or consent | s27(1)(d); NHA s71, s73 | Ethics approval letter; de-identification method |
| HLT-12 | Retention follows HPCSA Booklet 9 or the applicable law; disposal prevents reconstruction | s14(4), s14(5) | Retention schedule; disposal certificates |
| HLT-13 | Patient access requests handled (POPIA s23 and NHA s15 paths); identity verified proportionately | s23; NHA s15 | DSAR log |
| HLT-14 | Wearable data: only metrics needed for the feature; no sale or sharing for advertising; location off by default | s10, s15, s26 | SDK config; data map |
| HLT-15 | Children's health data has a competent person's consent or another s35 ground | s34, s35 | Consent records with competent_person_id |

## 6. Build patterns

### Separate health schema

```sql
-- s26/s32: special PI lives apart from account data, with its own policies and keys.
create schema if not exists health;

create table health.encounters (
  id              uuid primary key default gen_random_uuid(),
  patient_id      uuid not null references public.patients(id),
  practitioner_id uuid not null references public.practitioners(id),
  encounter_at    timestamptz not null,
  notes_enc       bytea,                 -- field-encrypted clinical notes
  icd10_enc       bytea,                 -- diagnosis codes encrypted too
  lawful_ground   text not null check (lawful_ground in ('s32_1_a_treatment','s27_1_a_consent','s27_1_b_legal')),
  created_at      timestamptz not null default now()
);
alter table health.encounters enable row level security;
alter table health.encounters force row level security;

-- treating practitioner only (s32(1)(a) "necessary for proper treatment and care")
create policy "treating practitioner" on health.encounters
  for select to authenticated
  using (practitioner_id = (select auth.uid()));

-- NHA s17 / s19: every read is logged
create table health.access_log (
  id bigserial primary key, actor uuid not null, patient_id uuid not null,
  record_table text not null, action text not null, at timestamptz not null default now()
);
```

### Consent wording (wellness app, s27(1)(a))

> ☐ I agree that ExampleFit (Pty) Ltd may process my heart rate, sleep and weight data to show my fitness trends in the app. This is health information. It is not shared with advertisers or my employer. I can withdraw this at any time in Settings, and my health data will then be deleted.

Separate, unticked, and not required to create an account if the core service works without it.

### Neutral reminders

```ts
// s19/s26: lock-screen safe. Never name the test, diagnosis or specialist.
const reminder = (firstName: string, when: string) =>
  `Hi ${firstName}, this is a reminder of your appointment on ${when}. Reply C to confirm.`;
```

### Telehealth session settings

```ts
const telehealthDefaults = {
  recording: false,                 // only with specific recorded consent
  transcriptToLLM: false,           // s72, s21: needs a DPA and region check first
  waitingRoom: true,
  consentCaptured: ['services', 'technology', 'prescribing'], // HPCSA Booklet 10
};
```

## 7. Retention (verify for your sector)

| Record | Period | Source | Status |
|---|---|---|---|
| Adult patient records | At least 6 years after the record becomes dormant | HPCSA Booklet 9 | In force (guideline) |
| Minors' records (and obstetric records) | Until the patient's 21st birthday | HPCSA Booklet 9 | In force (guideline) |
| Records of mentally incompetent patients | For the patient's lifetime | HPCSA Booklet 9 | In force (guideline) |
| Occupational health records | 20 years after treatment | HPCSA Booklet 9, citing OHSA | VERIFY against OHSA regulations |
| Long-latency exposure (e.g. asbestosis) | HPCSA recommends at least 25 years | HPCSA Booklet 9 | Guideline |
| Health information held by insurers, schemes, employers | No longer than needed, unless law, lawful function, contract or consent requires longer | Health Regulations 2026; s14 | In force |
| Telehealth recordings | Shortest period you can justify; treat as part of the record if kept | s14 | Recommended practice |
| Research datasets | Per ethics approval; de-identify as early as possible | s14(2); NHA s73 | VERIFY per protocol |

Any statutory period overrides the HPCSA guideline (Booklet 9 says so itself).

## 8. Scanner rule ideas

SPI-001 already flags special PI fields. Ideas to add:

| Idea | Detects | Severity | Section |
|---|---|---|---|
| Tracker on clinical routes | GA, Meta Pixel, Hotjar, Clarity loaded on routes matching `/appointments`, `/results`, `/patient`, `/consult` | High | s26, s72 |
| Diagnosis in message templates | SMS/WhatsApp/push templates containing `diagnos`, `HIV`, `oncology`, `pregnan`, `result` | Medium | s19, s26 |
| Unencrypted clinical columns | `notes`, `diagnosis`, `icd10`, `medication` as plain `text` in a health schema | Medium | s19 |
| Clinical text to LLM | `notes`/`diagnosis` variables passed to OpenAI/Anthropic/Gemini SDK calls | High | s26, s72 |
| Video recording default on | `recording: true` or `autoRecord` in telehealth SDK config | Medium | s26; HPCSA Booklet 10 |

## 9. Sources

Primary:
- POPIA Act 4 of 2013, ss 26, 27, 32, 34, 35, 57, 72, 112 (Government Gazette 37067, gov.za).
- Regulations relating to the Processing of Data Subjects' Health Information by Certain Responsible Parties, 2026: Notice 7198 of 2026, GG 54268, 6 March 2026 (inforegulator.org.za; acts.co.za).
- National Health Act 61 of 2003, ss 13 to 17, 71 to 73 (acts.co.za).
- HPCSA, Booklet 9: Guidelines on the Keeping of Patient Records (hpcsa.co.za).
- HPCSA, Booklet 10: Telehealth (hpcsa.co.za).
- Medical Schemes Act Regulations, Reg 15J (acts.co.za).
- Information Regulator, codes of conduct register (research code proposed 12 May 2023).

Secondary (context only):
- Moonstone, Fasken (April 2026), GoLegal: commentary on the Health Regulations 2026.
- Mediclinic: HPCSA telehealth summary (2020 amendments).

## 10. Open VERIFY items

- Regulation numbering and final content of the Health Regulations 2026 (legitimate interest assessment, notice before cross-border transfer).
- Current versions of HPCSA Booklets 5, 9 and 10.
- OHSA retention period for occupational health records.
- NHA s71 consent requirements in detail.

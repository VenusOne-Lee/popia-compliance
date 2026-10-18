> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# Education and children pack

**Last reviewed:** 2026-10-18. **Checklist prefix:** `EDU-`.

Status key: **In force** · **Published, not in force** · **Draft** · **Disputed / in court** · **VERIFY** (no primary source confirmed)

## 1. Who it's for

Builders of school administration and communication apps, learning management systems, edtech and tutoring platforms, homework and exam apps, school fee and transport apps, creches and aftercare tools, sports club and youth league apps, children's games, and any consumer product that may attract users under 18 (social, gaming, music, creator tools).

Children's information is a non-negotiable in `SKILL.md`: flag it before building and recommend a POPIA attorney for children's data at scale or across borders.

## 2. Laws beyond POPIA

| Law or instrument | What it means for builders | Status | Primary source |
|---|---|---|---|
| **POPIA s1 "child"** | A natural person **under 18** who is not legally competent, without the assistance of a competent person, to take any action or decision about themselves. | In force | Act text |
| **POPIA s1 "competent person"** | Any person legally competent to consent to any action or decision being taken about a child (typically a parent or guardian). | In force | Act text |
| **POPIA s34** | Prohibition: a responsible party may not process personal information concerning a child, subject to s35. | In force | Act text |
| **POPIA s35(1)** | Grounds: (a) prior consent of a competent person; (b) establishment, exercise or defence of a right or obligation in law; (c) international public law; (d) historical, statistical or research purposes with public interest or impracticability of consent, plus sufficient guarantees; (e) information deliberately made public by the child with a competent person's consent. | In force | Act text |
| **POPIA s35(2) and (3)** | The Regulator may authorise processing in the public interest, with conditions such as: let the competent person review the information and refuse further processing; give notice about the nature and processing of children's information; **refrain from encouraging or persuading a child to disclose more than is reasonably necessary**; keep reasonable integrity and confidentiality procedures. Treat these conditions as good practice even without an authorisation. | In force | Act text |
| **POPIA s57(1)(d)** | Prior authorisation needed to transfer children's information to a third party in a foreign country without adequate protection (as referred to in s72). | In force | Act text |
| **POPIA s32(1)(c) and (d)** | Schools may process health info where necessary for special support or arrangements; bodies managing the care of a child may process health info for their lawful duties. | In force | Act text |
| **Information Regulator Guidance Note on Processing Personal Information of Children** | Restates s34 and s35; explains public-interest authorisations and possible conditions. Does not set an age verification method and does not address behavioural advertising. | In force (guidance). Issued 2021 (exact date VERIFY) | inforegulator.org.za |
| **Children's Act 38 of 2005 s18** | Parental responsibilities and rights include guardianship and giving or refusing consent required by law. Where there is more than one guardian, each may generally act alone unless law or a court order says otherwise. | In force | Act text |
| **Children's Act s17** (age of majority 18) | Commonly cited as setting majority at 18. | VERIFY section number against Act text | Act text |
| **South African Schools Act 84 of 1996**, NCS Regulations R1114 of 2012, Reg 11 | Schools must keep learner profiles, report cards, schedules, teacher files and record sheets; the learner profile accompanies the learner through their schooling. No retention period stated in Reg 11. | In force | acts.co.za |
| **DBE Guidelines on POPIA** | DBE holds learner ID numbers and uses them for monitoring; linking ID numbers with other responsible parties' data needs prior authorisation. | In force (guidance). Date not stated | education.gov.za |
| **National Education Policy Act** | Limits DBE use of learner data to monitoring and evaluation (per DBE guideline). | In force (detail VERIFY) | education.gov.za |
| **Matric results publication (DBE matter)** | High Court set aside the Regulator's notices (Dec 2025); Regulator approached the SCA. Whether exam numbers are PI is unresolved. | Disputed / in court | See `references/10-regulatory-watch.md` |

## 3. Data categories and risk

| Data | Examples | Risk | Why |
|---|---|---|---|
| Any data about a child | Name, school, grade, class, photo, voice, location | **High** | s34 prohibition by default |
| Learner ID numbers | SA ID, LURITS number | **Critical** | Unique identifier; s57(1)(a) |
| Children's health and support needs | Allergies, chronic conditions, learning support, counselling notes | **Critical (special PI + child)** | s26, s32(1)(c), s34 |
| Location and transport | Live bus tracking, home address, pick-up times | **Critical** | Physical safety; s19 |
| Photos and video | Class photos, sports videos, livestreams | **High** | Identifiable images; social media reuse |
| Learning and behaviour analytics | Engagement scores, discipline records, proctoring video | **High** | Profiling; s71; s35(3)(c) |
| Parent and guardian data | Names, phones, ID numbers, custody arrangements | High | Custody details are sensitive; family conflict risk |
| Chat and messaging | Child to child, teacher to child | **High** | Safeguarding; s19 |
| Biometric attendance | Fingerprint or face check-in | **Critical (special PI + child)** | s26, s33, s34 |

## 4. Top 10 risky patterns builders ship

1. **No age question at all** in a consumer app that teenagers clearly use. You cannot claim you did not know (s34, s35).
2. **Age gate with a hint.** "You must be 18. Enter your birth year" with 18 pre-filled. A neutral DOB entry works better (`references/02-build-patterns.md` §11).
3. **"Parental consent" as a checkbox ticked by the child.** No verification that a competent person gave consent (s35(1)(a)).
4. **Behavioural advertising and tracking pixels** in a children's app or school platform. s35(3)(c) style conditions and the s69 guidance point against it. Do not do it.
5. **Public profiles and open messaging by default.** Strangers can find and message learners (s19).
6. **Gamified data collection.** Badges for "complete your profile", adding a school, hobbies and photos (s10, s35(3)(c)).
7. **School WhatsApp groups and spreadsheets** with learner names, ID numbers, medical notes and custody details shared to all parents (s19, s26).
8. **Edtech hosted offshore** with learner data and no s72 basis, and no assessment for s57(1)(d) (children's information to a country without adequate protection).
9. **AI tutors and proctoring** that send learner essays, voices or webcam video to an LLM or vision API with default retention or training (s15, s26 for biometrics, s72).
10. **Results and photos published online** without considering the DBE matric matter and parental consent (s11, s35).

## 5. Checklist

| ID | Control | POPIA | Evidence |
|---|---|---|---|
| EDU-01 | Audience decision recorded: product is for children, may attract children, or adults only | s34, s35 | PIA; product brief |
| EDU-02 | Neutral age gate for general-audience products; children found later are handled (consent or deletion) | s34, s35(1)(a) | Age gate screens; handling runbook |
| EDU-03 | Verifiable competent-person consent before collecting a child's information; consent record links the competent person | s35(1)(a), s11(2) | consent_events with competent_person_id; verification method |
| EDU-04 | Competent person can review the child's information and refuse further processing | s35(3)(a), s23, s24 | Parent dashboard or documented process |
| EDU-05 | Child-facing notice in plain language; parent-facing notice with s18 items | s18, s35(3)(b) | Notice text |
| EDU-06 | No behavioural advertising, no marketing pixels, no lookalike audiences built from children's data | s35(3)(c), s15, s69 | Tag config; site_check output |
| EDU-07 | Data collection limited to what the service needs; no gamified prompts to disclose more | s10, s35(3)(c) | Field inventory; UX review |
| EDU-08 | Privacy-protective defaults: private profiles, no stranger messaging, no location sharing, no public leaderboards with full names | s19 | Default settings config |
| EDU-09 | Learner ID numbers not collected unless required; if required, encrypted, masked and never used as a key; no cross-organisation linking without prior authorisation | s10, s19, s57(1)(a) | Schema; PIA |
| EDU-10 | Children's health and support data in a separate, restricted store with a s32(1)(c) or consent ground | s26, s32(1)(c) | Schema; RLS; ground record |
| EDU-11 | Cross-border hosting and vendors assessed for s72 and s57(1)(d) | s72, s57(1)(d) | Vendor register; authorisation if needed |
| EDU-12 | AI features (tutors, marking, proctoring) minimised; provider training off; no biometric processing without a s27 ground and attorney review | s15, s26, s72 | Provider settings; PIA |
| EDU-13 | Photos and video: separate consent for publication; easy removal | s11, s35(1)(a) | Consent records; takedown process |
| EDU-14 | Retention: delete when the learner leaves or the account closes, except records a law requires | s14 | Retention schedule; job |
| EDU-15 | Breach plan notifies competent persons (parents or guardians) for children's data | s22 | Incident runbook |

## 6. Build patterns

### Neutral age gate

```tsx
// s34/s35: ask DOB without revealing the threshold. Do not pre-fill. Do not store DOB if you only need a yes/no.
<Label htmlFor="dob">Date of birth</Label>
<Input id="dob" type="date" required onChange={e => setDob(e.target.value)} />
// server: compute age, store only age_band ('under_13' | '13_17' | '18_plus') and the date checked.
```

### Competent person consent

```sql
-- s35(1)(a): consent of a competent person, before processing. Append-only.
create table privacy.guardian_links (
  child_id           uuid not null references public.learners(id),
  guardian_id        uuid not null references public.guardians(id),
  relationship       text not null check (relationship in ('parent','guardian','court_appointed','other_competent')),
  verified_method    text not null check (verified_method in ('school_records','id_document_check','in_person','card_check')),
  verified_at        timestamptz not null,
  primary key (child_id, guardian_id)
);
-- consent_events.competent_person_id references the verified guardian (see references/02-build-patterns.md §3)
```

Flow:
1. Child or school starts sign-up. Collect only what is needed to contact the guardian (guardian email or phone).
2. Send the guardian a request with a plain notice (s18) and separate choices per purpose (service, photos, optional features).
3. Do not create the child's profile until the guardian consents. Delete pending requests after a short period (for example 14 days).
4. Give the guardian a dashboard to view, correct, download and delete (s35(3)(a)).

### Defaults for child accounts

```ts
export const childAccountDefaults = {
  profileVisibility: 'private',
  directMessages: 'teachers_and_approved_contacts_only',
  locationSharing: false,
  personalisedAds: false,       // and no ad SDKs loaded at all
  analytics: 'aggregate_only',  // no cross-site tracking, no session replay
  aiTrainingOnContent: false,
};
```

### School messaging

- Use role-based groups. Parents see their own child's information only.
- Never post learner lists with ID numbers, medical notes or custody details to a group chat.
- Teachers' devices: MFA and device lock. Exports of class lists are logged.

## 7. Retention (verify for your sector)

| Record | Period | Source | Status |
|---|---|---|---|
| Learner profile | Accompanies the learner through schooling | NCS Regulations R1114, Reg 11 | In force (period after leaving VERIFY) |
| Report cards, schedules, teacher files | Managed under the National Protocol for Assessment | NCS Regulations R1114, Reg 11 | Retention period VERIFY |
| Admission records | No period confirmed | South African Schools Act and provincial rules | VERIFY |
| Edtech accounts | Delete on account closure or when the school contract ends, with a short grace period | s14 | Recommended practice |
| Guardian consent records | For as long as processing continues plus a proof period | s11(2)(a) | Recommended practice |
| Pending guardian consent requests | Delete if not completed within a short period | s10, s14 | Recommended practice |
| Proctoring video | Delete after the review window | s14 | Recommended practice |
| Children's medical records at a health provider | Until age 21 | HPCSA Booklet 9 (see `health.md`) | Guideline |

## 8. Scanner rule ideas

CHI-001 already flags DOB, age and school fields. Ideas to add:

| Idea | Detects | Severity | Section |
|---|---|---|---|
| Ad SDKs in a child-directed app | AdMob, Meta Audience Network, AppLovin, Unity Ads alongside `child`, `learner`, `kids`, `grade` identifiers | High | s34, s35 |
| Pre-filled age threshold | `defaultValue` of 18 or a hint like "must be 13" next to a DOB field | Low | s35 |
| Guardian consent missing | Learner or child tables with no link to a guardian or consent table | Medium | s35(1)(a) |
| Public profile default | `is_public: true` or `visibility: 'public'` default on learner/child profiles | Medium | s19 |
| Learner ID as key | `learner_id_number` or `sa_id` as a primary key or URL param | High | s19, s57(1)(a) |

## 9. Sources

Primary:
- POPIA Act 4 of 2013, ss 1, 32, 34, 35, 57, 72 (Government Gazette 37067, gov.za).
- Information Regulator, Guidance Note on Processing Personal Information of Children (inforegulator.org.za; acts.co.za).
- Children's Act 38 of 2005, s18 (acts.co.za).
- Regulations pertaining to the National Curriculum Statement Grades R to 12, R1114 of 2012, Reg 11 (acts.co.za).
- Department of Basic Education, Guidelines on POPIA for DBE (education.gov.za).

Secondary:
- `references/10-regulatory-watch.md` on the matric results matter.

## 10. Open VERIFY items

- Exact date of the Regulator's children's guidance note.
- Children's Act section setting the age of majority.
- Retention periods for school assessment and admission records after a learner leaves.
- National Education Policy Act provision limiting DBE use of learner data.

> Engineering and compliance guidance, not legal advice. See DISCLAIMER.md.

# Short-term rentals pack

**Last reviewed:** 2026-10-18. **Checklist prefix:** `STR-`.

Status key: **In force** · **Published, not in force** · **Draft** · **Disputed / in court** · **VERIFY** (no primary source confirmed)

## 1. Who it's for

Airbnb and Booking.com hosts, guesthouses, B&Bs, lodges, holiday lets, serviced apartments, co-hosts, property management companies, and builders of guest check-in, direct booking, channel manager, smart lock and guest messaging tools in South Africa.

Most hosts are small businesses using phones, WhatsApp, Gmail and spreadsheets. That is still processing under POPIA. The household exclusion in s6 does not cover a paid accommodation business.

## 2. Laws beyond POPIA

| Law or instrument | What it means for builders | Status | Primary source |
|---|---|---|---|
| **Immigration Act 13 of 2002 s40(1)** | The person in charge of premises where lodging or sleeping accommodation is provided for payment or reward must, if the premises fall in a prescribed class, keep a register of everyone given lodging, in the prescribed manner. Each guest must sign it and give the prescribed particulars. | In force | Act text (acts.co.za) |
| **Immigration Act s40(2)** | The register must be produced for inspection when an immigration officer or police officer requires it. | In force | Act text |
| **Immigration Act s40(3)** | Failing to comply, giving false particulars, or hindering an officer is an offence: a fine or up to 12 months' imprisonment. | In force | Act text |
| **Immigration Regulations 2014 (GN R413), Reg 36** "Keeping of registers of lodgers by certain persons" | Prescribed classes: hotels and motels; boarding houses and lodges; guest houses; apartment buildings. Particulars per lodger: full names and surname; **a copy of the identification document or passport**; residence status in the Republic; normal residential address; signature. The register must be safeguarded by a duly authorised person for **two years**. | In force | acts.co.za (Reg 36) |
| Does Reg 36 cover a private home listed on Airbnb? | The prescribed classes name guest houses and apartment buildings. Whether a single house, cottage or flat let through a platform is in a prescribed class is not settled in any source we found. | **VERIFY** with an attorney | None found |
| **Draft Code of Good Practice for Short-Term Rentals** (GN 3824 of 2026, GG 54320, 13 Mar 2026) under s8 of the Tourism Act 3 of 2014 | Draft, non-binding, interim measure for public comment (60 days). Hosts: comply with all applicable laws including personal information law (para 4(c)); safety equipment, insurance, contact person. Platforms: give hosts guest contact and identity data "in line with relevant prescripts" (7(d)); handle host and guest data safely (7(h)); share host information with government subject to data protection law (7(i)). No guest register or ID verification rule. No CCTV rule. | Draft | GG 54320 |
| **Consumer Protection Act 68 of 2008** s17 | Consumer's right to cancel an advance reservation, booking or order. Relevant to booking terms, not data. | In force | Act text |
| **POPIA s69** | Post-stay "come back" emails and WhatsApp promotions need consent or the s69(3) customer exception (own similar services, opt-out at collection and on every message). | In force | Act text |
| **POPIA s72** | Guest data sent through WhatsApp (Meta), Gmail, Google Drive, US-hosted channel managers and smart lock clouds is usually a cross-border transfer. | In force | Act text |
| **Platform policies** (Airbnb) | Since 30 April 2024 Airbnb bans indoor security cameras in all listings regardless of disclosure; outdoor cameras are allowed with limits; noise monitors must be disclosed before booking. This is a contractual platform rule, not law. | In force (platform policy; current wording VERIFY on airbnb.com) | Airbnb policy; news reports March 2024 |
| **Municipal by-laws** (e.g. City of Cape Town short-term rental rules) | Municipalities may regulate zoning, rates and registration. Nothing found on guest data. | VERIFY per municipality | None found |
| **RICA (Act 70 of 2002)** and guest WiFi | Monitoring the content of guests' communications may be interception. Do not log browsing content. | In force; application to guest WiFi VERIFY | Act text |
| **Tax Administration Act** | Booking and income records for SARS. | In force | Act text |

## 3. Roles: platform, host, co-host, cleaner

| Party | Typical POPIA role | Notes |
|---|---|---|
| Platform (Airbnb, Booking.com) | Responsible party for its own processing (accounts, payments, ID verification it does) | The platform's notice covers the platform, not you |
| Host or guesthouse owner | **Responsible party** for anything you collect or keep yourself: ID copies, the register, WhatsApp chats, CCTV, smart lock logs, direct booking data | You need your own s18 notice and security |
| Property management company | Usually the responsible party if it runs the business and decides what to collect; an **operator** if it acts strictly on the owner's instructions | Write the role into the management agreement (s21) |
| Co-host | Operator for the host, or joint responsible party if they run the listing jointly | Agree in writing who keeps the register |
| Cleaners, maintenance, security, check-in agents | Operators or staff who see guest names, codes and IDs | Need-to-know only; written confidentiality terms (s20, s21) |
| Smart lock, CCTV, WiFi, channel manager, guest app vendors | Operators | DPA, hosting country, s72 basis |

## 4. Data categories and risk

| Data | Examples | Risk | Why |
|---|---|---|---|
| ID and passport copies | Photos of SA IDs, passports, visas | **Critical** | Identity fraud; unique identifiers; foreign nationals' immigration details |
| Residence status | Citizen, permanent resident, visitor | High | Immigration status is sensitive; required by Reg 36 only |
| Guest register | Names, addresses, signatures | High | Legal record; must be produced to officers |
| Contact and booking data | Phone, email, dates, party size | Medium | s69; s19 |
| Payment data | Card details for direct bookings, EFT proof, bank details | **Critical** | s105, s106; PCI DSS (see `fintech.md`) |
| Door codes and smart lock logs | Codes, entry and exit times | High | Physical safety; reveals movements |
| CCTV footage | Gate and driveway video, number plates | High | Images are PI; possible biometrics if face recognition is used (s26) |
| WiFi logs | Device MAC addresses, captive portal logins, browsing | Medium to high | Online identifiers (s1); RICA |
| Guest notes | Allergies, accessibility needs, celebrations, complaints | Medium to high | Health info is special PI (s26) |
| Children in the party | Names and ages of minors | High | s34, s35 |

## 5. Top 10 risky patterns hosts and builders ship

1. **"Send a photo of everyone's ID on WhatsApp."** IDs sit forever in phone galleries, WhatsApp backups (Google Drive or iCloud) and co-host chats (s19, s14, s72).
2. **Forwarding guest IDs to cleaners or security** so they "know who to expect". Share the name and arrival time only (s10, s19).
3. **ID copies in a shared Gmail inbox or Google Drive folder** with "anyone with the link" sharing (s19).
4. **Asking every guest for an ID copy** when the premises may not be in a prescribed class, or asking for more than Reg 36 lists (s10). If you rely on the Immigration Act, collect exactly the Reg 36 particulars.
5. **Keeping registers and IDs forever.** Reg 36 says two years. After that, delete unless another ground applies (s14).
6. **Indoor cameras, or undisclosed outdoor cameras and noise monitors.** Breaks Airbnb policy and s18 notice duties. Audio recording raises interception questions (VERIFY).
7. **Door codes reused across guests,** sent in plain email, and smart lock admin shared with former cleaners (s19).
8. **Guest WiFi captive portals** that collect email addresses for marketing with a pre-ticked box (s69; CON-002).
9. **Direct booking sites** that email card numbers or take card details over WhatsApp (s19, s105; PCI DSS).
10. **No breach process.** A lost phone with two years of guest IDs is a security compromise. Notify the Regulator and the guests (s22).

## 6. Checklist

| ID | Control | POPIA | Evidence |
|---|---|---|---|
| STR-01 | Role mapped: host, management company, co-host, platform. Written agreements say who is the responsible party and who is an operator | s20, s21 | Management agreement; co-host agreement |
| STR-02 | Legal basis for ID collection decided: Immigration Act s40 and Reg 36 (s11(1)(c)) if in a prescribed class, otherwise a documented reason or no collection | s10, s11 | Decision record; attorney note if unsure |
| STR-03 | Only the Reg 36 particulars collected for the register; no extra copies of other documents | s10 | Check-in form |
| STR-04 | IDs collected through a secure upload link or in person, not WhatsApp or plain email; stored encrypted in one place with access limited to named people | s19, s72 | Upload tool config; storage permissions |
| STR-05 | ID copies and register entries deleted or destroyed two years after the stay (Reg 36(2)), unless another ground applies; deletion covers phones, chats, email and backups | s14(4), s14(5) | Retention job or monthly checklist; deletion log |
| STR-06 | Guests get a short notice before arrival: what is collected, why (name the Immigration Act if relied on), who sees it, how long it is kept, their rights, and Regulator details | s18 | Pre-arrival message template; house manual |
| STR-07 | Cleaners, security and check-in staff receive only names, arrival times and party size; confidentiality terms signed | s10, s20, s21 | Message templates; signed undertakings |
| STR-08 | No indoor cameras. Outdoor cameras and noise monitors disclosed before booking and on signage; footage retention set; no face recognition | s18, s19, s26 | Listing text; camera settings; signage photo |
| STR-09 | Smart lock: unique code per stay, expires at check-out, entry logs retained briefly, admin access reviewed when staff change | s19, s14 | Lock app settings; access review |
| STR-10 | Guest WiFi does not log browsing content; captive portal (if any) uses unticked marketing consent | s10, s69 | Router config; portal screenshot |
| STR-11 | Post-stay marketing uses consent or the s69(3) customer exception with opt-out on every message | s69 | Consent records; message templates |
| STR-12 | Direct booking payments through a gateway; no card details by email, phone or WhatsApp | s19, s105 | Payment flow; staff instructions |
| STR-13 | Guest special needs (allergies, accessibility) kept only for the stay and deleted after | s10, s14, s26 | Notes retention |
| STR-14 | Lost phone, hacked email or leaked register handled as a s22 compromise | s22 | Incident runbook; eServices access |
| STR-15 | Foreign guests' passport and residence status data treated as high-risk; not shared beyond the register and officers who lawfully request it | s19, s11 | Access list; officer request log |

## 7. Build patterns

### Check-in form with Reg 36 particulars only

```tsx
{/* Immigration Act s40(1) + Reg 36: collect exactly these, nothing else (s10). */}
<form action="/api/checkin" method="post" encType="multipart/form-data">
  <Input name="full_names" label="Full names and surname" required />
  <Select name="residence_status" label="Residence status in South Africa" required
    options={['South African citizen', 'Permanent resident', 'Visitor or other']} />
  <Input name="residential_address" label="Normal residential address" required />
  <FileInput name="id_document" label="Copy of ID document or passport" accept="image/*,application/pdf" required />
  <SignaturePad name="signature" required />
  <p className="text-xs">
    We keep this register because the Immigration Act requires accommodation establishments to do so.
    Only the owner can see it. We delete it two years after your stay. See our <a href="/privacy">Privacy Notice</a>.
  </p>
</form>
```

### Register table

```sql
-- Immigration Act s40 / Reg 36. s19: private storage, encrypted. s14: purge after 2 years.
create table stay.lodger_register (
  id                  uuid primary key default gen_random_uuid(),
  booking_id          uuid not null references stay.bookings(id),
  full_names          text not null,
  residence_status    text not null check (residence_status in ('citizen','permanent_resident','visitor_other')),
  residential_address text not null,
  id_doc_object_key   text not null,       -- private bucket, encrypted, never a public URL
  signature_object_key text not null,
  signed_at           timestamptz not null,
  purge_after         date not null default ((current_date + interval '2 years')::date)
);
alter table stay.lodger_register enable row level security;
alter table stay.lodger_register force row level security;
create policy "owner only" on stay.lodger_register
  for select to authenticated
  using (exists (
    select 1 from stay.bookings b join stay.properties p on p.id = b.property_id
    where b.id = lodger_register.booking_id and p.owner_id = (select auth.uid())
  ));

-- nightly: delete expired rows and their storage objects (storage delete runs in an edge function)
delete from stay.lodger_register where purge_after < current_date;
```

### Pre-arrival notice (WhatsApp or email)

> Hi Thandi, we look forward to hosting you on 12 December. South African law requires guesthouses to keep a register of guests with a copy of an ID or passport. Please upload it here: [secure link]. Please do not send ID photos on WhatsApp. Only the owner sees the register, and we delete it two years after your stay. Our privacy notice: [link].

### What to send the cleaner

> Booking 14 to 16 Dec, 3 guests, arriving about 15:00. Code changes at 11:00 on the 16th.

No surname, no phone number, no ID.

### Phone hygiene for small hosts

- Turn off WhatsApp auto-download to the gallery for business chats.
- Delete ID photos from the phone, WhatsApp chat and cloud backup once uploaded to the register.
- Use a separate business number. Enable screen lock and remote wipe.

## 8. Retention (verify for your sector)

| Record | Period | Source | Status |
|---|---|---|---|
| Guest register with ID or passport copy | Safeguarded for 2 years | Immigration Regulations 2014, Reg 36(2) | In force (applies to prescribed classes) |
| Booking and income records | Generally 5 years | Tax Administration Act | Commonly cited norm |
| CCTV footage | Short rolling window (for example 30 days) unless an incident is under investigation | s14 | Recommended practice |
| Smart lock entry logs | Short window (for example 90 days) | s14 | Recommended practice |
| WiFi connection logs | Shortest period needed for network security | s14 | Recommended practice; RICA VERIFY |
| Guest special needs notes | Until check-out | s14 | Recommended practice |
| ID copies sent outside the register (WhatsApp, email) | Delete immediately after transfer to the register | s14, s19 | Recommended practice |

## 9. Scanner rule ideas

| Idea | Detects | Severity | Section |
|---|---|---|---|
| ID upload to public bucket | Storage bucket named `ids`, `passports`, `guest-docs`, `checkin` with `public: true` | Critical | s19 |
| Unbounded register retention | Register or check-in tables with no `purge_after`, `deleted_at` or retention job | Medium | s14 |
| WhatsApp deep link asking for ID | `wa.me/...?text=` containing `ID`, `passport` | Low | s19, s72 |
| Card fields in booking form | `card_number`, `cvv` inputs in a booking or check-in form | High | s19, s105 |
| Indoor camera config | Camera names like `lounge`, `bedroom`, `kitchen` in CCTV or smart home config | Medium | s19; platform policy |

## 10. Sources

Primary:
- Immigration Act 13 of 2002, s40 (acts.co.za).
- Immigration Regulations 2014, GN R413, Reg 36 Keeping of register (acts.co.za).
- Department of Tourism, Draft Code of Good Practice for Short-Term Rentals, General Notice 3824 of 2026, GG 54320, 13 March 2026.
- POPIA Act 4 of 2013, ss 6, 10, 11, 14, 18 to 22, 26, 34, 35, 69, 72, 105 (gov.za).
- Consumer Protection Act 68 of 2008, s17 (acts.co.za).

Secondary (context only):
- Hotel Management Network (Nov 2024) on the Immigration Act register.
- IOL (27 Mar 2026) on the draft Code.
- OPB and others (11 Mar 2024) on Airbnb's indoor camera ban.

## 11. Open VERIFY items

- Whether a private home or single unit listed on a platform falls within a Reg 36 prescribed class.
- Current Airbnb camera and noise monitor policy wording.
- Municipal short-term rental by-laws (Cape Town and others) and any guest data rules.
- RICA application to guest WiFi monitoring and audio-capable devices.
- Final status of the draft Code of Good Practice after the comment period.

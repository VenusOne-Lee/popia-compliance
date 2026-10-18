# Security compromise response (s22)

Use this the moment someone says "leak", "hack", "exposed", "wrong recipient", "lost laptop", "ransomware", "public bucket", "RLS was off".

**Key facts**
- Trigger: **reasonable grounds to believe** PI has been **accessed or acquired by an unauthorised person**. Certainty is not required. You don't need proof of misuse.
- Notify **both** the Information Regulator and affected data subjects, **as soon as reasonably possible** after discovery. There is **no risk-of-harm threshold**: the Regulator's fact sheet (Aug 2025) states reporting is mandatory.
- Regulator notifications go through the **eServices portal** (mandatory since 1 April 2025). Email and the old SCN1 form are not accepted.
- Report on what you know; **update** the notification as facts emerge.
- If it happened at an **operator**, the operator tells you; **you** notify.
- Delay is only allowed if a public body responsible for investigating offences, or the Regulator, determines notification would impede a criminal investigation.
- Most common causes per the Regulator (2026): weak security controls, human error, weak passwords, malware/ransomware, phishing.
- Not notifying is itself enforced: Lancet Laboratories (repeated unreported compromises) and CJC (2026) enforcement notices.

## Playbook

### Hour 0 to 4: Contain and preserve
1. Assign an incident lead and inform the **Information Officer / Deputy IO**.
2. Contain: revoke leaked keys, rotate credentials, enable RLS / make bucket private, disable compromised accounts, isolate hosts. **Don't wipe** evidence.
3. Preserve: snapshot affected systems, export relevant logs (auth, DB, storage access, CDN), note timestamps (SAST).
4. Start the incident log: who, what, when, decisions, evidence locations.

### Hour 4 to 48: Scope
5. What PI categories? (ID numbers, account numbers, health, special PI, children's info, credentials raise severity.)
6. How many data subjects? Which ones? Can you identify them?
7. Was it accessed/acquired? (Logs: was the exposed endpoint/bucket actually hit by unknown IPs? If you can't tell, assume yes.)
8. Who are the unauthorised parties, if known?
9. Is an operator involved? Request their incident report under the contract.
10. Is it also a crime? Consider a SAPS case (Cybercrimes Act). Financial institutions/ECSPs: check whether s54 Cybercrimes Act reporting has commenced and applies; sector regulators (FSCA/PA, SARB) may have their own reporting duties.

### As soon as reasonably possible: Notify
11. **Regulator** via eServices portal (Information Officer logs it). Have ready: responsible party and IO details, date/time of compromise and discovery, description, PI categories, number of data subjects, likely consequences, measures taken, recommendations to data subjects, whether data subjects were notified, operator involvement.
12. **Data subjects** in writing (email, mail, prominent website notice, news media, or as Regulator directs). Content required by s22(5):
    - description of the **possible consequences**;
    - **measures** you've taken or intend to take;
    - **recommendations** for what they should do to mitigate (change passwords, watch for phishing, SAFPS protective registration, contact bank);
    - **identity of the unauthorised person**, if known.
   Templates: `templates/breach-notice-data-subject.md`.
13. Website notice: keep it up for a reasonable period and say how people can get help.
14. Other parties: insurers (cyber policy notice windows are often short), banks/payment providers if card or account data, clients (if you're the operator), sector regulators.

### After: Learn
15. Root cause analysis; fix the class of issue, not just the instance.
16. Update the Regulator notification with final findings.
17. Update risk register, controls, training. Run the scanner across all repos for the same pattern.
18. Keep the incident file. The Regulator may assess you later (SABS 2026: no incident response plan was itself a finding).

## Severity cues

| Data involved | Extra steps |
|---|---|
| Passwords/credentials | Force reset; check for reuse; MFA prompt |
| SA ID numbers | Recommend SAFPS protective registration; credit bureau alerts |
| Bank/card | Notify bank/PSP; s105/106 offence risk; PCI incident process |
| Health/special PI | Plain-language, sensitive notice; consider support line |
| Children | Notify competent persons (parents/guardians) |
| Large scale / public | Media holding statement ready; Regulator may direct publicity |

## Common builder incidents

- **RLS off / open API** found by a researcher or scanner: still a compromise if logs show (or can't rule out) unauthorised access. Check access logs before deciding; if no logs exist, assume access.
- **Service key in public repo**: rotate immediately; review DB logs for use of that key.
- **Misdirected email with a spreadsheet**: request deletion confirmation from recipient; still notify (CJC 2026 enforcement notice arose from one misdirected email).
- **Preview deployment with prod data**: take down; check access logs; notify if accessed or unknown.
- **Leaked .env in Docker image / client bundle**: rotate every secret in it.

## Audit checks

| ID | Check |
|---|---|
| BR-01 | Written incident response plan with s22 steps and named roles |
| BR-02 | IO/DIO registered and able to log on eServices portal |
| BR-03 | Operator contracts require immediate notification |
| BR-04 | Logs sufficient to determine access (retained long enough) |
| BR-05 | Notification templates ready (Regulator data, data subjects, website) |
| BR-06 | Tabletop exercise in last 12 months |
| BR-07 | Past compromises were notified (check incident history) |
| BR-08 | Key/credential rotation runbook exists |

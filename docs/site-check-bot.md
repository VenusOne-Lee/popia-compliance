# The POPIA Kit site checker

If you found `popia-site-check` in your logs or your firewall, this page says what it is, what it asks for, and how to allow or block it.

## What it is

The POPIA Kit site check looks at a live website for privacy and security leads: HTTPS, security headers, cookies set before consent, trackers and links to a privacy notice and PAIA manual. Someone ran it on your site, either at [popiakit.co.za/check](https://popiakit.co.za/check) or with `popia-kit site-check` on their own machine.

It sends this User-Agent:

```
popia-site-check/1.0 (+https://github.com/VenusOne-Lee/popia-compliance/blob/main/docs/site-check-bot.md; passive)
```

## What it requests

Every request is an ordinary GET, the kind a browser makes.

- The page that was entered, following up to 5 redirects.
- `http://` on the same host, without following the redirect, to see whether plain HTTP sends visitors to HTTPS.
- `/.well-known/security.txt`.
- The CLI, and the hosted check when its operator turns it on, also try a few common notice paths such as `/privacy`, `/paia` and `/cookies`.

That is 2 to 11 requests per check. It does not run JavaScript, submit forms, log in, or keep the cookies your site sets. The hosted check never stores or logs the address or the result.

## It respects your firewall

If your bot protection answers with a challenge or a block, the check stops and says nothing was checked. It does not retry, solve the challenge, change its User-Agent or try from other addresses. A bot check page is never graded as if it were your site.

## How to allow it

Only do this for your own site. Anyone can send this User-Agent, so a rule that matches it lets anyone who copies it past your bot protection. Allow it while you run a check, then turn the rule off.

Vercel: in Firewall, add a custom rule. If User Agent contains `popia-site-check`, then Bypass. Save and publish the rule, run the check, then disable it.

Cloudflare: in Security, WAF, custom rules, add a rule with the expression `(http.user_agent contains "popia-site-check")` and the action Skip, for the bot and challenge features you use. Run the check, then disable it.

Other providers have a similar allow or bypass rule on the User-Agent.

The hosted check runs on shared cloud addresses that change, so there is no fixed IP list to allow. If you would rather not open your firewall at all, you have two options that bot protection does not affect:

- Run the check yourself from a network you already trust: `uvx popia-kit site-check https://your-site.co.za`
- Scan your code instead: `uvx popia-kit scan .`

## How to block it

Add a deny rule for User-Agents that contain `popia-site-check`. The check will then report that it could not read your site.

## Contact

Questions or abuse reports: popiakit@venusone.africa. POPIA Kit is a project of Venus ARC (Pty) Ltd, trading as Venus One.

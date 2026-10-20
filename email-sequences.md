# Email sequences — Invoice Chaser

Placeholders: `{{client_name}}`, `{{document}}`, `{{deadline}}`, `{{accountant_name}}`, `{{firm_name}}`

---

## Stage 1 — Polite first reminder

**Subject:** Quick reminder: {{document}} still needed

Hi {{client_name}},

Just a quick reminder that we are still waiting on {{document}} to complete your file. If you could send it over at your earliest convenience, that would be great.

Reply to this email if anything is unclear, happy to help.

Thanks,
{{accountant_name}}
{{firm_name}}

---

## Stage 2 — Firmer reminder with deadline

**Subject:** Second reminder: {{document}} needed by {{deadline}}

Hi {{client_name}},

Following up on {{document}}. We need this by {{deadline}} to stay on schedule with your filing, and delays here can push back your submission.

Could you please send it over today, or let me know when to expect it?

Thanks,
{{accountant_name}}
{{firm_name}}

---

## Stage 3 — Final notice

**Subject:** Final notice: outstanding {{document}}

Hi {{client_name}},

This is our final automated reminder regarding {{document}}. We have not received it despite two earlier reminders, and this is now holding up your file.

{{accountant_name}} will be in touch directly to resolve this.

Regards,
{{firm_name}}

---

## Escalation email (to the accountant, not the client)

**Subject:** Escalation: {{client_name}} unresponsive after 3 follow-ups

Escalation needed: {{client_name}} ({{client_email}}) has not responded to 3 follow-ups about '{{document}}'. Last sent: {{last_sent}}. Please contact them directly.

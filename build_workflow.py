"""Builds n8n-workflow.json programmatically so the JSON is always valid.
Run: python3 build_workflow.py
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "n8n-workflow.json")

SHEET_ID = "PASTE_TRACKER_SHEET_ID_HERE"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=PASTE_GEMINI_API_KEY_HERE"


def node(nid, name, ntype, tv, pos, params, notes="", creds=True, on_error=None):
    n = {
        "id": nid,
        "name": name,
        "type": ntype,
        "typeVersion": tv,
        "position": list(pos),
        "parameters": params,
    }
    if notes:
        n["notes"] = notes
    if creds:
        n["credentials"] = {}
    if on_error:
        n["onError"] = on_error
    return n


def conn(name, idx=0):
    return {"node": name, "type": "main", "index": idx}


SUBJECT_EXPR = (
    '{{ ["Quick reminder: " + $json.document_needed + " still needed", '
    '"Second reminder: " + $json.document_needed + " needed this week", '
    '"Final notice: outstanding " + $json.document_needed][$json.followup_stage] }}'
)

BODY_T1 = (
    '"Hi " + $json.client_name + ",\\n\\n" + '
    '"Just a quick reminder that we are still waiting on " + $json.document_needed + '
    '" to complete your file. If you could send it over at your earliest convenience, that would be great." + '
    '"\\n\\nReply to this email if anything is unclear, happy to help.\\n\\nThanks"'
)
BODY_T2 = (
    '"Hi " + $json.client_name + ",\\n\\n" + '
    '"Following up on " + $json.document_needed + ". " + '
    '"We need this by end of week to stay on schedule with your filing, and delays here can push back your submission." + '
    '"\\n\\nCould you please send it over today, or let me know when to expect it?\\n\\nThanks"'
)
BODY_T3 = (
    '"Hi " + $json.client_name + ",\\n\\n" + '
    '"This is our final automated reminder regarding " + $json.document_needed + ". " + '
    '"We have not received it despite two earlier reminders, and this is now holding up your file." + '
    '"\\n\\nYour accountant will be in touch directly to resolve this.\\n\\nRegards"'
)
BODY_EXPR = "{{ [" + BODY_T1 + ", " + BODY_T2 + ", " + BODY_T3 + "][$json.followup_stage] }}"

nodes = [
    node(
        "sched-1", "Daily 9am Check", "n8n-nodes-base.scheduleTrigger", 1.2, [200, 300],
        {"rule": {"interval": [{"field": "hours", "hoursInterval": 24, "triggerAtDay": True}]}},
        notes="Runs every day at 9:00. Set the workflow timezone to the firm's timezone.",
        creds=False,
    ),
    node(
        "sheets-read-1", "Read Tracker", "n8n-nodes-base.googleSheets", 4, [400, 300],
        {
            "operation": "read",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_ID},
            "sheetName": {"__rl": True, "mode": "name", "value": "Tracker"},
        },
        notes="ADD YOUR Google Sheets OAuth2 credential here. Document ID = the Invoice Chaser tracker sheet.",
    ),
    node(
        "code-filter-1", "Filter Due Rows", "n8n-nodes-base.code", 2, [620, 300],
        {
            "jsCode": (
                "const ACTIVE = ['awaiting', 'f1_sent', 'f2_sent', 'final_sent'];\n"
                "const today = new Date(); today.setHours(0,0,0,0);\n"
                "return items.filter(item => {\n"
                "  const s = (item.json.status || '').trim();\n"
                "  if (!ACTIVE.includes(s)) return false;\n"
                "  const raw = item.json.next_followup;\n"
                "  if (!raw) return true;\n"
                "  const d = new Date(raw); d.setHours(0,0,0,0);\n"
                "  return d <= today;\n"
                "});"
            )
        },
        notes="Keeps only rows still being chased AND due today or earlier. Everything else is ignored.",
        creds=False,
    ),
    node(
        "loop-1", "Loop Rows", "n8n-nodes-base.splitInBatches", 3, [820, 300],
        {"batchSize": 1, "options": {}},
        notes="One client at a time, so a failure on one row never blocks the others.",
        creds=False,
    ),
    node(
        "code-route-1", "Decide Route", "n8n-nodes-base.code", 2, [1020, 300],
        {
            "jsCode": (
                "return items.map(item => {\n"
                "  const stage = Number(item.json.followup_stage || 0);\n"
                "  item.json.route = stage >= 3 ? 'escalate' : 'email';\n"
                "  return item;\n"
                "});"
            )
        },
        notes="Stage 0-2 -> send the next follow-up email. Stage 3 -> stop emailing, escalate to the accountant.",
        creds=False,
    ),
    node(
        "if-escalate-1", "Needs Escalation?", "n8n-nodes-base.if", 2, [1220, 300],
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                "conditions": [
                    {
                        "id": "e1",
                        "leftValue": "={{ $json.route }}",
                        "rightValue": "escalate",
                        "operator": {"type": "string", "operation": "equals", "name": "equals"},
                    }
                ],
            },
            "options": {},
        },
        creds=False,
    ),
    node(
        "set-email-1", "Build Email", "n8n-nodes-base.set", 3, [1420, 180],
        {
            "mode": "manual",
            "include": "all",
            "assignments": {
                "assignments": [
                    {"id": "a-subject", "name": "subject", "type": "string", "value": SUBJECT_EXPR},
                    {"id": "a-body", "name": "body", "type": "string", "value": BODY_EXPR},
                    {"id": "a-next", "name": "next_stage", "type": "number", "value": "={{ $json.followup_stage + 1 }}"},
                    {"id": "a-status", "name": "next_status", "type": "string",
                     "value": '{{ ["f1_sent", "f2_sent", "final_sent"][$json.followup_stage] }}'},
                    {"id": "a-today", "name": "today", "type": "string", "value": "={{ $now.toISO().slice(0,10) }}"},
                ]
            },
            "options": {},
        },
        notes="Picks subject/body for the client's current stage. Stage 0 -> template 1, stage 1 -> template 2, stage 2 -> template 3.",
        creds=False,
    ),
    node(
        "http-gemini-1", "Personalize with Gemini", "n8n-nodes-base.httpRequest", 4, [1620, 180],
        {
            "method": "POST",
            "url": GEMINI_URL,
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                '={"contents": [{"parts": [{"text": "Write ONE warm, professional opening sentence '
                "for a payment-reminder email to a client called '\" + $json.client_name + \"' about outstanding '\" "
                '+ $json.document_needed + "\'. No greeting, just the sentence, under 20 words.\"}]}]}'
            ),
            "options": {"timeout": 15000},
        },
        notes="ADD YOUR Gemini API key in the URL. On ANY error this node continues with the error output, and the IF node falls back to the static template. The send NEVER depends on the AI.",
        creds=False,
        on_error="continueRegularOutput",
    ),
    node(
        "if-gemini-1", "Gemini OK?", "n8n-nodes-base.if", 2, [1820, 180],
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                "conditions": [
                    {
                        "id": "g1",
                        "leftValue": "={{ $json.candidates }}",
                        "operator": {"name": "exists", "operation": "exists", "type": "object"},
                    }
                ],
            },
            "options": {},
        },
        notes="If Gemini returned a usable sentence, use it. Otherwise fall back to the static template.",
        creds=False,
    ),
    node(
        "set-merge-1", "Merge AI Line", "n8n-nodes-base.set", 3, [2020, 80],
        {
            "mode": "manual",
            "include": "all",
            "assignments": {
                "assignments": [
                    {"id": "m-body", "name": "body", "type": "string",
                     "value": "={{ $json.candidates[0].content.parts[0].text + \"\\n\\n\" + $('Build Email').item.json.body }}"},
                ]
            },
            "options": {},
        },
        notes="Prepends the Gemini-written opening line to the template body.",
        creds=False,
    ),
    node(
        "gmail-send-1", "Send Follow-up", "n8n-nodes-base.gmail", 2, [2220, 180],
        {
            "resource": "message",
            "emailType": "text",
            "subject": "={{ $json.subject }}",
            "message": "={{ $json.body }}",
            "sendTo": "={{ $json.client_email }}",
            "options": {},
        },
        notes="ADD YOUR Gmail OAuth2 credential here. Sends from the firm's Gmail account.",
        on_error="continueErrorOutput",
    ),
    node(
        "sheets-update-1", "Update Tracker Row", "n8n-nodes-base.googleSheets", 4, [2420, 180],
        {
            "operation": "update",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_ID},
            "sheetName": {"__rl": True, "mode": "name", "value": "Tracker"},
            "columns": {
                "mappingMode": "defineBelow",
                "matchingColumns": ["client_email"],
                "value": {
                    "client_email": "={{ $json.client_email }}",
                    "followup_stage": "={{ $json.next_stage }}",
                    "last_sent": "={{ $json.today }}",
                    "status": "={{ $json.next_status }}",
                },
            },
        },
        notes="ADD YOUR Google Sheets OAuth2 credential here. Advances the row: stage +1, status updated, last_sent = today.",
        on_error="continueErrorOutput",
    ),
    node(
        "sheets-log-1", "Log Email", "n8n-nodes-base.googleSheets", 4, [2620, 180],
        {
            "operation": "append",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_ID},
            "sheetName": {"__rl": True, "mode": "name", "value": "Email Log"},
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "timestamp": "={{ $now.toISO() }}",
                    "client_email": "={{ $json.client_email }}",
                    "stage": "={{ $json.next_stage }}",
                    "subject": "={{ $json.subject }}",
                    "status": "sent",
                },
            },
        },
        notes="ADD YOUR Google Sheets OAuth2 credential here. Appends every send to the Email Log tab for audit.",
    ),
    node(
        "gmail-esc-1", "Escalate to Accountant", "n8n-nodes-base.gmail", 2, [1420, 440],
        {
            "resource": "message",
            "emailType": "text",
            "subject": '={{ "Escalation: " + $json.client_name + " unresponsive after 3 follow-ups" }}',
            "message": (
                '={{ "Escalation needed: " + $json.client_name + " (" + $json.client_email + ") " + '
                '"has not responded to 3 follow-ups about \'" + $json.document_needed + "\'. " + '
                '"Last sent: " + $json.last_sent + ". Please contact them directly." }}'
            ),
            "sendTo": "={{ $json.accountant_email }}",
            "options": {},
        },
        notes="ADD YOUR Gmail OAuth2 credential here. After 3 unanswered follow-ups the accountant gets a summary and the automation stops emailing the client.",
        on_error="continueErrorOutput",
    ),
    node(
        "sheets-esc-1", "Mark Escalated", "n8n-nodes-base.googleSheets", 4, [1620, 440],
        {
            "operation": "update",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_ID},
            "sheetName": {"__rl": True, "mode": "name", "value": "Tracker"},
            "columns": {
                "mappingMode": "defineBelow",
                "matchingColumns": ["client_email"],
                "value": {
                    "client_email": "={{ $json.client_email }}",
                    "status": "escalated",
                    "notes": "Escalated after 3 unanswered follow-ups",
                },
            },
        },
        notes="ADD YOUR Google Sheets OAuth2 credential here. Flags the row as escalated so it leaves the chase loop.",
    ),
    node(
        "gmail-alert-1", "Alert Owner", "n8n-nodes-base.gmail", 2, [2020, 640],
        {
            "resource": "message",
            "emailType": "text",
            "subject": "Invoice Chaser: automation error needs attention",
            "message": (
                "Invoice Chaser hit an error. Check the Email Log tab (status=failed) for details. "
                "The failing item's data is attached to this run's error output."
            ),
            "sendTo": "PASTE_OWNER_EMAIL_HERE",
            "options": {},
        },
        notes="ADD YOUR Gmail OAuth2 credential here. Wire each risky node's ERROR output (second output) into this node.",
    ),
    node(
        "sheets-fail-1", "Log Failure", "n8n-nodes-base.googleSheets", 4, [2220, 640],
        {
            "operation": "append",
            "documentId": {"__rl": True, "mode": "id", "value": SHEET_ID},
            "sheetName": {"__rl": True, "mode": "name", "value": "Email Log"},
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "timestamp": "={{ $now.toISO() }}",
                    "client_email": "={{ $json.client_email || 'unknown' }}",
                    "stage": "={{ $json.followup_stage || '' }}",
                    "subject": "={{ 'FAILED: ' + ($json.subject || 'send step') }}",
                    "status": "failed",
                },
            },
        },
        notes="ADD YOUR Google Sheets OAuth2 credential here. Failures are logged, never silent.",
    ),
]

connections = {
    "Daily 9am Check": {"main": [[conn("Read Tracker")]]},
    "Read Tracker": {"main": [[conn("Filter Due Rows")]]},
    "Filter Due Rows": {"main": [[conn("Loop Rows")]]},
    "Loop Rows": {"main": [[], [conn("Decide Route")]]},
    "Decide Route": {"main": [[conn("Needs Escalation?")]]},
    "Needs Escalation?": {"main": [[conn("Escalate to Accountant")], [conn("Build Email")]]},
    "Escalate to Accountant": {
        "main": [[conn("Mark Escalated")], [conn("Alert Owner")]]
    },
    "Mark Escalated": {"main": [[conn("Loop Rows")]]},
    "Build Email": {"main": [[conn("Personalize with Gemini")]]},
    "Personalize with Gemini": {"main": [[conn("Gemini OK?")]]},
    "Gemini OK?": {"main": [[conn("Merge AI Line")], [conn("Send Follow-up")]]},
    "Merge AI Line": {"main": [[conn("Send Follow-up")]]},
    "Send Follow-up": {
        "main": [[conn("Update Tracker Row")], [conn("Alert Owner")]]
    },
    "Update Tracker Row": {
        "main": [[conn("Log Email")], [conn("Alert Owner")]]
    },
    "Log Email": {"main": [[conn("Loop Rows")]]},
    "Alert Owner": {"main": [[conn("Log Failure")]]},
}

workflow = {
    "name": "Invoice Chaser - Accounting Follow-up Automation",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1"},
    "staticData": None,
}

with open(OUT, "w") as f:
    json.dump(workflow, f, indent=2)

# verify
with open(OUT) as f:
    d = json.load(f)
print("OK:", len(d["nodes"]), "nodes,", len(d["connections"]), "connections ->", OUT)

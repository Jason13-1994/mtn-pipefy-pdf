---
title: Triggers, webhook contract and EC2 deployment
last_updated: 2026-08-18
---

# 04 — Triggers and deployment

EC2 is not provisioned yet. Build order is therefore: **CLI proves the documents →
box goes up → automations get wired last.** Nothing in Pipefy changes until the
three PDFs are signed off.

---

## 1. The triggers

One Pipefy automation per pipe: *card moves to phase X* → *call the service*.

| Pipe | Fires on entry to | Phase id | Why there |
|---|---|---|---|
| Campaign Planning `307284211` | **Approved Campaigns** | `343906152` | The campaign is now fact. `CP008` already fires here to create the DB record. |
| Campaign Briefing `307284210` | **Brief Submitted** | `343906142` | The brief has cleared approval. **See the ordering problem below.** |
| Agency Workflow `307284207` | **Backlog** | `343906124` | Card creation phase. The agency card exists and `creative_team` is already set. |

### ⚠ The ordering problem on Campaign Briefing

Entry to Brief Submitted `343906142` already fires the 17 agency fan-out
automations, and each of them copies `brief_attached` from the briefing card to
the agency card. If the Job Brief PDF is *also* generated on entry to that phase,
the two race: the fan-out most likely copies the **previous** (or empty) value.

Three ways out, in order of preference:

1. **Generate the Job Brief earlier** — on the approving decision, i.e. entry to
   Brief Submitted is preceded by the last `job_review_decision` being set. Fire on
   the field-change event instead of the move. Clean, but a second event type.
2. **Let it race and don't care** — the Agency Brief is generated independently on
   the agency card, so a stale `brief_attached` copy only matters if MTN wants the
   Job Brief on the agency card as a fallback (**D1**). If it doesn't, drop
   `brief_attached` from the fan-out field map entirely and the problem disappears.
3. **Service fans out** — the Job Brief handler writes the PDF to the briefing card
   *and* to its child agency cards. Most control, most code, and it duplicates what
   the automation already does.

**Recommendation: (2) plus (1) if MTN want the fallback.** Decide with **D1**.

### Automation shape

`event: card_moved` → `action: http_request` (Pipefy's webhook action), or a
`card_moved` webhook subscription pointed at the service. Payload as Pipefy sends
it; the service reads `data.card.id`. Naming convention consistent with what is
there (`J1xx`, `CP0xx`):

```
PDF01 | Approved Campaigns      | Generate Campaign Brief PDF
PDF02 | Brief Submitted         | Generate Job Brief PDF
PDF03 | Agency card created     | Generate Agency Brief PDF
```

Add the same guard the fan-out uses — `last_phase_in != <previous phase>` — so a
card bouncing back and forth doesn't regenerate on every hop.

---

## 2. Webhook contract

```
POST /pipefy/generate-pdf
Header: X-MTN-PDF-Token: <shared secret>        # not in the Up & Up version — add it
```

Accepts either shape:

```json
{"card_id": 1425600095}
{"data": {"card": {"id": 1425600095}}}
```

Response `200`:

```json
{
  "card_id": "1425600095",
  "profile": "agency",
  "document": "Agency Brief",
  "filename": "Agency Brief - Curiosity - Uni Activations - 1425600095.pdf",
  "attached_to": "agency_brief_attached",
  "verified": true,
  "duration_ms": 2840
}
```

| Code | Meaning |
|---|---|
| `200` | Rendered, uploaded, attached, **and re-read to confirm** |
| `202` | Rendered and attached, verification read-back failed — needs a look |
| `400` | No card id in payload |
| `401` | Bad or missing token |
| `404` | Card not found |
| `409` | Card is in a pipe with no profile |
| `422` | Render refused — e.g. Agency Brief with no `creative_team` |
| `500` | Anything else |

**Differences from the Up & Up service, deliberate:**

- Returns **JSON, not the PDF bytes.** Pipefy doesn't consume the body, and a
  400KB response per call is waste. `GET /pipefy/preview/{card_id}` returns bytes
  for humans.
- **Shared-secret header.** The Up & Up endpoint is unauthenticated on a public
  IP. Do not repeat that here.
- **Verifies after attaching** — re-reads the card and confirms the file is on
  the field. The existing CLI already does this; keep it.

Also:

```
GET  /health                      -> {"status":"healthy","version":"...","profiles":3}
GET  /pipefy/preview/{card_id}    -> PDF bytes, attaches nothing (support tool)
POST /pipefy/generate-pdf?dry=1   -> renders, reports, attaches nothing
```

---

## 3. Idempotency and retries

Pipefy retries a failed webhook. `updateCardField` on an attachment field
**overwrites**, so a retry is naturally idempotent — the card ends up with one
current PDF either way. Two guards worth having:

- **In-flight lock per card id** (in-process dict + TTL) so a double-fire renders
  once, not twice.
- **`--keep-existing` equivalent off by default.** One current brief per card.
  Re-running replaces rather than stacking, and the log records what it removed.

---

## 4. The EC2 box

Mirror the Up & Up host so there is one thing to operate, not two.

| | |
|---|---|
| Instance | `t3.small` (t3.micro is tight once reportlab and two logos are resident) |
| OS | Ubuntu 24.04 LTS |
| Region | Match the Up & Up box (`us-east-2`) unless MTN data residency says otherwise — **open question, [05](05_gaps-risks-open-questions.md) D6** |
| Python | 3.12, venv at `/home/ubuntu/mtn-pipefy-pdf/venv` |
| Service | systemd `mtn-pipefy-pdf.service`, uvicorn on `:8000`, `Restart=always` |
| Ingress | **443 only**, via Caddy or nginx + Let's Encrypt. Not `:8000` on the open internet. |
| Egress | `api.pipefy.com`, the Pipefy S3 presign host, Papertrail |
| Secrets | `EnvironmentFile=/home/ubuntu/mtn-pipefy-pdf/.env`, `chmod 600`, root-owned |
| Logs | journald + Papertrail HTTP, same as Up & Up |
| Backup | None needed — stateless. Rebuild from the repo. |

```ini
# deploy/mtn-pipefy-pdf.service
[Unit]
Description=MTN Pipefy PDF Generator
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/mtn-pipefy-pdf
EnvironmentFile=/home/ubuntu/mtn-pipefy-pdf/.env
ExecStart=/home/ubuntu/mtn-pipefy-pdf/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Note `--host 127.0.0.1`, not `0.0.0.0` — the reverse proxy is the only thing that
should reach uvicorn.

### Environment

```bash
MTN_PIPEFY_TOKEN=          # Pipefy PAT. Needs WRITE on all three pipes.
MTN_PIPEFY_ORG_ID=302505741
MTN_PDF_WEBHOOK_SECRET=    # matches X-MTN-PDF-Token
PAPERTRAIL_TOKEN=          # optional
LOG_LEVEL=INFO
```

**Token.** A dedicated service account, not a person's PAT — a PAT dies when
someone leaves and the failure is a silent stop to brief generation. A read-only
token renders fine and fails at the attach step, which is a confusing way to find
out. → **D7**.

### Observability

Minimum for handover:

- One structured log line per request: `card_id`, `profile`, `outcome`, `ms`, `error`
- A CSV/SQLite run log (`card_id, filename, timestamp, result`) — support's first
  question is always "did it run for this card?"
- `/health` on an uptime check
- Papertrail alert on `ERROR` rate, and on **zero generations in 24h on a weekday**
  — the failure mode that matters is silence, not noise.

---

## 5. Deployment runbook (goes in `deploy/RUNBOOK.md`)

```bash
# provision
ssh -i <key>.pem ubuntu@<host>
sudo apt update && sudo apt install -y python3.12-venv git caddy
git clone https://github.com/<org>/mtn-pipefy-pdf.git
cd mtn-pipefy-pdf && python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env && nano .env
sudo cp deploy/mtn-pipefy-pdf.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now mtn-pipefy-pdf

# verify
curl -s localhost:8000/health
./venv/bin/python cli.py <known_card_id>          # dry run, no writes

# deploy a change
git pull && ./venv/bin/pip install -r requirements.txt
./venv/bin/python tools/check_drift.py            # must pass before restart
sudo systemctl restart mtn-pipefy-pdf
sudo journalctl -u mtn-pipefy-pdf -n 50 --no-pager
```

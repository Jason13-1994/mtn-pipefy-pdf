# SERVER_SETUP — mtn-pipefy-pdf

EC2 + systemd + Nginx. No database — the service is stateless and rebuilds from
the repo.

| | |
|---|---|
| Instance | `t3.small`, Ubuntu 24.04 LTS |
| Path | `/home/ubuntu/mtn-pipefy-pdf` |
| Service | `mtn-pipefy-pdf.service`, uvicorn on `127.0.0.1:5040` |
| Proxy | Nginx on 443, Certbot for TLS |
| Secrets | `segredo.ini`, `chmod 600`, git-ignored |
| Logs | journald + Papertrail |

**`mtn-pdf.dydx.digital` throughout this document is an illustrative example
hostname, not an authoritative one.** It appears at multiple points below
(the Certbot `-d` flag in section 4, the automation URL in section 6, the
retrigger `curl` example in section 8). Replace every occurrence with your
own real hostname before use -- a partial find-and-replace leaves one command
pointed at a hostname that is not yours. `nginx.conf.example` uses its own
separate `<your-hostname-here>` placeholder for `server_name`; that file is
edited independently, see section 4.

---

## 1. Provision

```bash
ssh -i <key>.pem ubuntu@<host>
```

```bash
sudo apt update && sudo apt install -y python3-venv nginx
```

Generate a read-only SSH deploy key on the box, then register its public
half with the repo -- the box has no clone access until this is done:

```bash
ssh-keygen -t ed25519 -C "mtn-pipefy-pdf-box" -f ~/.ssh/mtn_pipefy_deploy -N ""
```

Print the public key and paste it into the repo's GitHub Settings -> Deploy
keys -> Add deploy key. Leave **"Allow write access" unchecked** -- this key
must stay read-only.

```bash
cat ~/.ssh/mtn_pipefy_deploy.pub
```

Append an SSH config entry so the `git clone` below picks up the non-default
key filename with no extra flags:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/mtn_pipefy_deploy
    IdentitiesOnly yes
EOF
```

```bash
cd /home/ubuntu && git clone git@github.com:Jason13-1994/mtn-pipefy-pdf.git mtn-pipefy-pdf && cd mtn-pipefy-pdf
```

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

## 2. Configure

```bash
cp segredo.ini.example segredo.ini && chmod 600 segredo.ini && nano segredo.ini
```

Fill in:

| Key | Value |
|---|---|
| `[Pipefy] token` | Service-account token. Write on `307284210` and `307284211`, read on `mOUzRnnK`. **Not a personal PAT** — a PAT dies when someone leaves, and the failure is silent: briefs stop generating and agencies stop receiving them. |
| `[Service] webhook_secret` | Long random string, minimum 20 characters. The Pipefy automation sends it as `X-MTN-PDF-Token`. The service refuses to start without one on any non-loopback bind. |
| `[Service] replay_token` | Separate long random string, for deliberate retriggers. |
| `[PaperTrail] papertrail_log_token` | Per-project token. |

## 3. Service

```bash
sudo cp /home/ubuntu/mtn-pipefy-pdf/mtn-pipefy-pdf.service /etc/systemd/system/
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now mtn-pipefy-pdf
```

```bash
sudo systemctl status mtn-pipefy-pdf --no-pager
```

## 4. Nginx

`/etc/nginx/sites-available/mtn-pipefy-pdf`

Copy `nginx.conf.example` from the repo to that path, then edit `server_name`
to your real hostname. `nginx.conf.example` is the single source of truth for
the proxy shape -- the request body-size cap, the rate limit scoped to
`/generate-pdf`, and the proxy headers all live there, not duplicated in
this document.

```bash
sudo cp /home/ubuntu/mtn-pipefy-pdf/nginx.conf.example /etc/nginx/sites-available/mtn-pipefy-pdf && sudo nano /etc/nginx/sites-available/mtn-pipefy-pdf
```

```bash
sudo ln -s /etc/nginx/sites-available/mtn-pipefy-pdf /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
```

```bash
sudo certbot --nginx -d mtn-pdf.dydx.digital
```

uvicorn binds `127.0.0.1` only. Nginx is the only thing that should reach it.

---

## 5. Verify before wiring any automation

```bash
curl -s -X POST http://127.0.0.1:5040/hello
```

```bash
cd /home/ubuntu/mtn-pipefy-pdf && ./venv/bin/python check_drift.py
```

```bash
./venv/bin/python make_pdf.py <known_card_id>
```

That last one is a dry run — it renders to `./out` and writes nothing to Pipefy.
Open the PDF before going further.

```bash
./venv/bin/python make_pdf.py <known_card_id> --apply
```

Exit `0` means uploaded, attached, and confirmed by a read-back. **This is the
first time the presigned upload path runs against live** — if anything fails,
it will fail here.

---

## 6. Wire the Pipefy automations

Only after both documents are signed off. Campaign Planning first — lower
volume and nothing downstream depends on it.

| Name | Pipe | Event | Action |
|---|---|---|---|
| `PDF01 \| Campaign Review \| Generate Campaign Brief PDF` | `307284211` | card moved to `343906151` | HTTP POST |
| `PDF02 \| Brief Review - 1st Approval \| Generate Job Brief PDF` | `307284210` | card moved to `343906141` | HTTP POST |

```
URL     https://mtn-pdf.dydx.digital/generate-pdf
Header  X-MTN-PDF-Token: <webhook_secret>
Body    {"data": {"card": {"id": "%{card_id}"}}}
```

Do **not** add a `last_phase_in` guard. The agency fan-out uses one to avoid
duplicate cards; generation *wants* to re-fire when a brief comes back through
Brief Updates, so the approver and the agencies see the amended version.

After PDF02 goes live, take one brief all the way through to Brief Submitted and
confirm the agency cards carry the current PDF. That is the test that matters.

---

## 7. Deploy a change

```bash
cd /home/ubuntu/mtn-pipefy-pdf && git pull && ./venv/bin/pip install -r requirements.txt
```

```bash
./venv/bin/python check_drift.py
```

```bash
sudo systemctl restart mtn-pipefy-pdf && sudo journalctl -u mtn-pipefy-pdf -n 50 --no-pager
```

`check_drift.py` must pass before the restart. It is the only thing standing
between a Pipefy form change and a brief that has quietly stopped being complete.

---

## 8. Support

**"Did it run for this card?"** — search Papertrail for the keyword
`mtn_pipefy_pdf` and the card id. Every run logs one line; every failure logs
the raw inbound payload in `details`, which is what a retrigger replays.

**Retrigger a failed run.** Take the raw payload out of the Papertrail
`details`, then:

```bash
curl -X POST https://mtn-pdf.dydx.digital/generate-pdf \
  -H "X-MTN-PDF-Token: <webhook_secret>" \
  -H "X-MTN-Replay-Token: <replay_token>" \
  -H "Content-Type: application/json" \
  -d '{"data":{"card":{"id":"<card_id>"}}}'
```

This hits a live card and replaces the attachment on it. Confirm the card id
before sending, and never bulk-replay a range without going card by card.

**Alerts worth having:** `/hello` on an uptime check, a Papertrail alert on the
error rate, and one on **zero generations in 24h on a weekday** — the failure
mode that costs money here is silence, not noise.

**Do not add `--workers N` to the systemd unit's `ExecStart` line.**
`my_state.py`'s in-flight/dedup lock only coordinates within a single
process — multiple uvicorn workers would not share it, and the
duplicate-render race the lock exists to prevent would silently come back.

**Restart:**

```bash
sudo systemctl restart mtn-pipefy-pdf
```

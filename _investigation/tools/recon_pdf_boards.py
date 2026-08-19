#!/usr/bin/env python3
"""
recon_pdf_boards.py — READ-ONLY structural dump of the three PDF-generation
boards plus the Campaign Planning DB.

Writes:
    recon_live.json          full raw structure
    01_board-structures.LIVE.md   regenerated field inventory, diffable against
                                  the committed 01a_field-inventory.md

Run this on YOUR machine. api.pipefy.com is not reachable from the Claude
sandbox, so the token never leaves your laptop.

    python recon_pdf_boards.py
    python recon_pdf_boards.py --pipes 307284207 --out ./scratch

Token resolution: MTN_PIPEFY_TOKEN / PIPEFY_ACCESS_TOKEN / PIPEFY_TOKEN env var,
then a .env or .env.txt next to this script, then the same in the parent folder.

THIS SCRIPT PERFORMS NO WRITES. It issues query operations only; there is no
mutation anywhere in this file.
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = "https://api.pipefy.com/graphql"
_CTX = ssl.create_default_context()
TOKEN_VARS = ("MTN_PIPEFY_TOKEN", "PIPEFY_ACCESS_TOKEN", "PIPEFY_TOKEN")

ORG_ID = "302505741"
PIPES = {
    "307284211": "Campaign Planning",
    "307284210": "Campaign Briefing",
    "307284207": "Agency Workflow",
}
TABLES = {"mOUzRnnK": "Campaign Planning DB"}

# Fields that must never reach a rendered document.
JUNK_IDS = {"button", "field", "field_1", "field_2", "field_3", "field_4", "_", "__1"}

INVIS = re.compile(r"[​‌‍‎‏﻿]")


def clean(s):
    return re.sub(r"\s+", " ", INVIS.sub("", s or "")).strip()


def section_title(desc):
    """Zero-width-label fields carry the section name in their description."""
    for line in (desc or "").splitlines():
        line = re.sub(r"^#+\s*", "", line.strip().strip("_").strip()).strip()
        if line:
            return clean(line)
    return None


def load_token(here):
    for var in TOKEN_VARS:
        if os.environ.get(var):
            return os.environ[var].strip()
    parent = os.path.dirname(here)
    for d in (here, parent, os.path.dirname(parent)):
        for name in (".env", ".env.txt"):
            try:
                with open(os.path.join(d, name), "r", encoding="utf-8-sig") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        if k.strip() in TOKEN_VARS:
                            return v.strip().strip('"').strip("'")
            except (FileNotFoundError, NotADirectoryError):
                continue
    sys.exit(
        "ERROR: no Pipefy token found.\n"
        "Set MTN_PIPEFY_TOKEN=<token> as an environment variable, or put it in a\n"
        ".env file next to this script."
    )


class Pipefy(object):
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def gql(self, query, variables=None, tries=0):
        self.calls += 1
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Authorization": "Bearer %s" % self.token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=60) as r:
                payload = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and tries < 4:
                time.sleep(2 ** tries)
                return self.gql(query, variables, tries + 1)
            sys.exit("HTTP %s from Pipefy: %s" % (e.code, e.read().decode()[:400]))
        if payload.get("errors"):
            return payload.get("data"), payload["errors"]
        return payload.get("data"), None


FIELD_FRAGMENT = """
  id internal_id uuid label type options required editable
  description index is_multiple minimal_view
"""

PIPE_QUERY = """
query($id: ID!) {
  pipe(id: $id) {
    id name description public startFormPhaseId
    labels { id name }
    start_form_fields { %s }
    phases { id name done fields { %s } }
    startFormFieldConditions {
      id name
      actions { actionId whenEvaluator phaseField { id internal_id label } }
      condition { expressions { field_address operation value structure_id }
                  expressions_structure }
    }
  }
}""" % (FIELD_FRAGMENT, FIELD_FRAGMENT)

TABLE_QUERY = """
query($id: ID!) {
  table(id: $id) {
    id name description public url
    table_fields { %s }
  }
}""" % FIELD_FRAGMENT

AUTOMATION_QUERY = """
query($id: ID!) {
  pipe(id: $id) {
    automations {
      id name active action_id event_id
      event_params action_params condition
      action_repo_v2 { ... on Pipe { id name } }
    }
  }
}"""


def resolve_conditions(pipe):
    """Turn internal_id references into readable field ids."""
    by_int = {}
    for f in pipe.get("start_form_fields") or []:
        by_int[f["internal_id"]] = f["id"]
    for ph in pipe.get("phases") or []:
        for f in ph.get("fields") or []:
            by_int[f.get("internal_id")] = f.get("id")
    out = []
    for c in pipe.get("startFormFieldConditions") or []:
        exprs = (c.get("condition") or {}).get("expressions") or []
        out.append({
            "name": c.get("name"),
            "sources": [by_int.get(e.get("field_address"), e.get("field_address"))
                        for e in exprs],
            "tests": [(e.get("operation"), e.get("value")) for e in exprs],
            "shows": [a["phaseField"]["id"] for a in (c.get("actions") or [])
                      if a.get("actionId") == "show" and a.get("whenEvaluator")],
            "hides": [a["phaseField"]["id"] for a in (c.get("actions") or [])
                      if a.get("actionId") == "hide"],
        })
    return out


def markdown(data):
    L = ["<!-- generated by tools/recon_pdf_boards.py — do not hand-edit -->",
         "# Board structures (LIVE)", "",
         "Captured: %s" % data["captured_at"],
         "Org: `%s`" % data["org_id"], ""]
    for pid, pipe in data["pipes"].items():
        if not pipe:
            L += ["## %s `%s` — NOT READABLE" % (PIPES.get(pid, "?"), pid), ""]
            continue
        sff = pipe.get("start_form_fields") or []
        L += ["## %s — `%s`" % (pipe.get("name"), pid), "",
              "%d start-form fields, %d phases." % (len(sff), len(pipe.get("phases") or [])), "",
              "**Phases:** " + " → ".join("%s `%s`" % (p["name"], p["id"])
                                          for p in pipe.get("phases") or []), "",
              "| Section | Field id | Label | Type | Req | Opts |",
              "|---|---|---|---|---|---|"]
        cur = "_(pre-section)_"
        for f in sff:
            lab = clean(f.get("label"))
            if not lab:
                s = section_title(f.get("description"))
                if s:
                    cur = s
                    continue
                lab = "**JUNK (blank label)**"
            junk = " **JUNK**" if f["id"] in JUNK_IDS else ""
            nopt = len(f.get("options") or [])
            L.append("| %s | `%s` | %s%s | %s | %s | %s |" % (
                cur, f["id"], lab, junk, f["type"],
                "Y" if f.get("required") else "", nopt or ""))
        L += ["", "### Phase fields", "", "| Phase | Field id | Label | Type |", "|---|---|---|---|"]
        for ph in pipe.get("phases") or []:
            for f in ph.get("fields") or []:
                if f.get("type") == "statement":
                    continue
                L.append("| %s | `%s` | %s | %s |" % (
                    ph["name"], f.get("id"),
                    clean(f.get("label")) or "**JUNK (blank label)**", f.get("type")))
        conds = data["conditions"].get(pid) or []
        if conds:
            L += ["", "### Start-form conditions (%d)" % len(conds), "",
                  "| Rule | When | Shows |", "|---|---|---|"]
            for c in conds:
                L.append("| %s | `%s` %s | %s |" % (
                    c["name"], ", ".join(c["sources"]),
                    " ".join("%s %r" % t for t in c["tests"]),
                    ", ".join("`%s`" % s for s in c["shows"]) or "—"))
        autos = data["automations"].get(pid) or []
        if autos:
            L += ["", "### Automations (%d)" % len(autos), "",
                  "| Active | Event | Action | Name |", "|---|---|---|---|"]
            for a in autos:
                L.append("| %s | %s | %s | %s |" % (
                    "on" if a.get("active") else "**off**",
                    a.get("event_id"), a.get("action_id"), a.get("name")))
        L.append("")
    for tid, tbl in data["tables"].items():
        if not tbl:
            continue
        L += ["## Table %s — `%s`" % (tbl.get("name"), tid), "",
              "%d fields. %s" % (len(tbl.get("table_fields") or []), tbl.get("url") or ""), "",
              "| Field id | Label | Type |", "|---|---|---|"]
        for f in tbl.get("table_fields") or []:
            L.append("| `%s` | %s | %s |" % (
                f.get("id"), clean(f.get("label")) or "**JUNK (blank label)**", f.get("type")))
        L.append("")
    return "\n".join(L) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Read-only recon of the MTN PDF boards.")
    ap.add_argument("--pipes", nargs="*", default=sorted(PIPES),
                    help="pipe ids (default: all three)")
    ap.add_argument("--tables", nargs="*", default=sorted(TABLES))
    ap.add_argument("--out", default=here, help="output directory")
    ap.add_argument("--no-automations", action="store_true")
    args = ap.parse_args()

    pf = Pipefy(load_token(here))
    me, err = pf.gql("{ me { name email } }")
    if err:
        sys.exit("Token rejected: %s" % json.dumps(err)[:300])
    print("=" * 72)
    print("  READ-ONLY RECON — no mutations are issued by this script")
    print("  token : %s" % (me or {}).get("me", {}).get("name", "?"))
    print("  pipes : %s" % ", ".join(args.pipes))
    print("=" * 72)

    data = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "org_id": ORG_ID,
        "pipes": {}, "tables": {}, "conditions": {}, "automations": {},
        "warnings": [],
    }

    for pid in args.pipes:
        print("  pipe %s ..." % pid, end=" ", flush=True)
        d, err = pf.gql(PIPE_QUERY, {"id": pid})
        if err or not (d or {}).get("pipe"):
            data["warnings"].append("pipe %s: %s" % (pid, json.dumps(err)[:200]))
            data["pipes"][pid] = None
            print("FAILED")
            continue
        pipe = d["pipe"]
        data["pipes"][pid] = pipe
        data["conditions"][pid] = resolve_conditions(pipe)
        print("%s — %d start-form fields" % (pipe["name"], len(pipe["start_form_fields"])))

        if not args.no_automations:
            d2, err2 = pf.gql(AUTOMATION_QUERY, {"id": pid})
            if err2:
                data["warnings"].append("automations %s: %s" % (pid, json.dumps(err2)[:200]))
            else:
                data["automations"][pid] = ((d2 or {}).get("pipe") or {}).get("automations") or []

    for tid in args.tables:
        print("  table %s ..." % tid, end=" ", flush=True)
        d, err = pf.gql(TABLE_QUERY, {"id": tid})
        tbl = (d or {}).get("table")
        data["tables"][tid] = tbl
        if err or not tbl:
            data["warnings"].append("table %s: %s" % (tid, json.dumps(err)[:200]))
            print("FAILED")
        else:
            print("%s — %d fields" % (tbl["name"], len(tbl["table_fields"])))

    os.makedirs(args.out, exist_ok=True)
    jpath = os.path.join(args.out, "recon_live.json")
    mpath = os.path.join(args.out, "01_board-structures.LIVE.md")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    with open(mpath, "w", encoding="utf-8") as fh:
        fh.write(markdown(data))

    print("-" * 72)
    print("  %d API calls" % pf.calls)
    print("  wrote %s" % jpath)
    print("  wrote %s" % mpath)
    if data["warnings"]:
        print("  WARNINGS:")
        for w in data["warnings"]:
            print("    - %s" % w)
    print("\n  Next: diff 01_board-structures.LIVE.md against 01a_field-inventory.md")
    print("  Anything that moved is a config change before the build starts.")


if __name__ == "__main__":
    main()

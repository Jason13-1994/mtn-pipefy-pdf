'''
     check_drift.py — does my_layout.py still match the live Pipefy forms?

     my_layout.py is an allowlist: a field nobody has added to it does not
     appear in a document. That is deliberate — it is what keeps a stray form
     field out of a brief an external agency reads — but it means the document
     can silently fall behind the form. This is the thing that tells you.

          python check_drift.py                 exit 1 on any drift
          python check_drift.py --profile brief
          python check_drift.py --scaffold 307284210 > draft_layout.txt

     Read-only. Issues query operations only; there is no mutation in this file.
     Run it in CI on every push, and weekly on a schedule.

     MISSING  on the live form, absent from my_layout.py
              -> the brief has quietly stopped being complete. Add the field,
                 or add it to set_deny so the decision is on the record.
     STALE    in my_layout.py, absent from the live form
              -> renamed or deleted in Pipefy. A rename shows up as a MISSING
                 and a STALE together.
     DENIED   on the form and explicitly excluded. Reported, never a failure.
'''
import argparse
import sys

import my_funcs
import my_layout
import my_pipefy

# Blank-label placeholders and form furniture. Present on the live forms,
# never printable, and not worth reporting as MISSING every single run.
L_IGNORED_TYPES = ["statement"]


def fn_live_field_ids(stamp, o_doc=None) -> tuple:
     '''
          {field_id: {"label", "type"}} for every printable field on the pipe —
          start form and phase fields. Returns (d_fields, n_status).
     '''
     try:
          d_pipe, n_status = my_pipefy.fn_fetch_pipe_form(stamp=stamp,
                                                          s_pipe_id=o_doc.s_pipe_id)
          if n_status != 200:
               return {}, n_status
          d_fields = {}
          l_all = list(d_pipe.get("start_form_fields") or [])
          for d_phase in d_pipe.get("phases") or []:
               l_all += list(d_phase.get("fields") or [])
          for d_field in l_all:
               s_field_id = d_field.get("id")
               s_label = my_funcs.fn_tidy(d_field.get("label") or "")
               if not s_field_id or not s_label:
                    continue          # zero-width label = section header
               if d_field.get("type") in L_IGNORED_TYPES:
                    continue
               d_fields[s_field_id] = {"label": s_label, "type": d_field.get("type") or ""}
          return d_fields, 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Drift check field read failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "pipe_id": o_doc.s_pipe_id})
          return {}, 500


def fn_live_table_field_ids(stamp, o_doc=None) -> tuple:
     '''
          {field_id: {"label", "type"}} for the linked Campaign Planning DB.
          ({}, 204) when the profile has no campaign connector.
          Returns (d_fields, n_status).
     '''
     try:
          s_table_id = (o_doc.d_campaign or {}).get("s_table_id") or ""
          if not s_table_id:
               return {}, 204
          d_table, n_status = my_pipefy.fn_fetch_table_fields(stamp=stamp,
                                                              s_table_id=s_table_id)
          if n_status != 200:
               return {}, n_status
          d_fields = {}
          for d_field in d_table.get("table_fields") or []:
               s_field_id = d_field.get("id")
               s_label = my_funcs.fn_tidy(d_field.get("label") or "")
               if not s_field_id or not s_label:
                    continue
               d_fields[s_field_id] = {"label": s_label, "type": d_field.get("type") or ""}
          return d_fields, 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Drift check table read failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e)})
          return {}, 500


def fn_check_profile(stamp, o_doc=None) -> tuple:
     '''
          Compare one profile against its live form, and its campaign-summary
          fields against the linked table.

          The two scopes are compared separately on purpose. The Job Brief's
          campaign summary reads campaign_objective and friends off the
          Campaign Planning DB, not off the briefing pipe — checked against the
          pipe they would all report STALE, and the report would be noise
          nobody reads.

          Returns (d_report, n_status).
     '''
     try:
          d_live, n_status = fn_live_field_ids(stamp=stamp, o_doc=o_doc)
          if n_status != 200:
               return {}, n_status

          set_in_layout = my_layout.fn_allowed_field_ids(o_doc=o_doc, s_scope="pipe")
          set_denied = set(o_doc.set_deny)
          set_live = set(d_live)

          l_missing = sorted(set_live - set_in_layout - set_denied)
          l_stale = sorted((set_in_layout | set_denied) - set_live)
          l_denied_live = sorted(set_denied & set_live)

          # Campaign-summary fields, against the table they are actually read from.
          l_campaign_stale = []
          i_campaign_live = 0
          d_table_live, n_table_status = fn_live_table_field_ids(stamp=stamp, o_doc=o_doc)
          if n_table_status == 200:
               set_campaign = my_layout.fn_allowed_field_ids(o_doc=o_doc, s_scope="campaign")
               i_campaign_live = len(d_table_live)
               l_campaign_stale = sorted(set_campaign - set(d_table_live))

          return {
               "profile": o_doc.s_key,
               "document": o_doc.s_doc_title,
               "pipe_id": o_doc.s_pipe_id,
               "live_fields": len(set_live),
               "in_layout": len(set_in_layout),
               "missing": [{"id": s_id, **d_live[s_id]} for s_id in l_missing],
               "stale": l_stale,
               "denied": l_denied_live,
               "campaign_live_fields": i_campaign_live,
               "campaign_stale": l_campaign_stale,
          }, 200
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Drift check failed at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "profile": getattr(o_doc, "s_key", "")})
          return {}, 500


def fn_print_report(d_report=None) -> int:
     '''
          Print one profile's report. Returns the number of differences.
     '''
     try:
          l_missing = d_report.get("missing") or []
          l_stale = d_report.get("stale") or []
          l_denied = d_report.get("denied") or []
          l_campaign_stale = d_report.get("campaign_stale") or []
          print(f"\n{d_report.get('document')} ({d_report.get('pipe_id')})"
                f"    {d_report.get('live_fields')} live / "
                f"{d_report.get('in_layout')} in layout")
          if l_missing:
               print("  MISSING  on the form, not in my_layout.py:")
               for d_field in l_missing:
                    print(f"    {d_field['id']:<52} {d_field['type']:<20} {d_field['label']}")
          if l_stale:
               print("  STALE    in my_layout.py, not on the form:")
               for s_id in l_stale:
                    print(f"    {s_id}")
          if l_campaign_stale:
               print(f"  STALE    in the campaign summary, not on the linked table "
                     f"({d_report.get('campaign_live_fields')} table fields):")
               for s_id in l_campaign_stale:
                    print(f"    {s_id}")
          if l_denied:
               print(f"  DENIED   on the form, explicitly excluded: "
                     f"{len(l_denied)} field(s)  (ok)")
          if not l_missing and not l_stale and not l_campaign_stale:
               print("  OK — layout and form agree.")
          return len(l_missing) + len(l_stale) + len(l_campaign_stale)
     except Exception:
          return 1


def fn_scaffold(stamp, s_pipe_id="") -> int:
     '''
          Emit a starter layout block from the live form, grouped by the form's
          own section headers, so a new profile does not have to be typed out by
          hand. Paste it into my_layout.py and curate. Returns an exit code.
     '''
     try:
          d_pipe, n_status = my_pipefy.fn_fetch_pipe_form(stamp=stamp, s_pipe_id=s_pipe_id)
          if n_status != 200:
               print(f"Could not read pipe {s_pipe_id}.")
               return 1
          print(f"     # scaffolded from {d_pipe.get('name')} ({s_pipe_id}) — CURATE THIS")
          print("     l_sections=[")
          b_open = False
          for d_field in d_pipe.get("start_form_fields") or []:
               s_label = my_funcs.fn_tidy(d_field.get("label") or "")
               if not s_label:
                    s_section = my_funcs.fn_section_title_from_description(
                         s_description=d_field.get("description") or "")
                    if s_section:
                         if b_open:
                              print("          ]),")
                         print(f'          Section("{s_section}", [')
                         b_open = True
                    else:
                         print(f'          # JUNK, blank label: {d_field.get("id")}')
                    continue
               s_render = ', s_render="block"' if d_field.get("type") == "long_text" else ""
               print(f'               Field("{d_field.get("id")}"{s_render}),'
                     f'   # {d_field.get("type")}')
          if b_open:
               print("          ]),")
          print("     ],")
          return 0
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          print(f"Scaffold failed at line {e_traceback.tb_lineno}: {e}")
          return 1


def fn_main() -> int:
     '''
          Returns 0 when layout and forms agree, 1 on drift or error.
     '''
     try:
          o_parser = argparse.ArgumentParser(
               description="Compare my_layout.py against the live Pipefy forms.")
          o_parser.add_argument("--profile", default="",
                                choices=sorted(my_layout.D_PROFILE_BY_KEY) + [""],
                                help="check one profile instead of all")
          o_parser.add_argument("--scaffold", default="",
                                help="pipe id — print a starter layout block and exit")
          o_parser.add_argument("--quiet-log", action="store_true",
                                help="print log lines instead of sending to Papertrail")
          d_args = o_parser.parse_args()

          stamp = my_funcs.fn_build_stamp(s_mode="PrintOnly" if d_args.quiet_log else "")

          if d_args.scaffold:
               return fn_scaffold(stamp=stamp, s_pipe_id=d_args.scaffold)

          l_docs = ([my_layout.fn_profile_for_key(s_key=d_args.profile)]
                    if d_args.profile else my_layout.L_PROFILES)
          i_differences = 0
          for o_doc in l_docs:
               d_report, n_status = fn_check_profile(stamp=stamp, o_doc=o_doc)
               if n_status != 200:
                    print(f"\n{o_doc.s_doc_title} ({o_doc.s_pipe_id})    "
                          f"COULD NOT BE CHECKED — Pipefy returned {n_status}")
                    i_differences += 1
                    continue
               i_differences += fn_print_report(d_report=d_report)

          print("")
          if i_differences:
               print(f"FAIL — {i_differences} difference(s). Add or deny each field in "
                     f"my_layout.py, then re-run.")
               return 1
          print("PASS — every profile matches its live form.")
          return 0

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          print(f"check_drift failed at line {e_traceback.tb_lineno}: {e}")
          return 1


if __name__ == "__main__":
     sys.exit(fn_main())

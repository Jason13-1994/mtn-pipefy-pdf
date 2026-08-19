'''
     make_pdf.py — command line front end for the same code the webhook runs.

     Exists because main.py's __main__ block is a single uvicorn.run() call and
     cannot carry argument parsing, and because the documents have to be proven
     and signed off before any automation is pointed at the service. Also the
     backfill tool.

          python make_pdf.py 1425600095                 dry run, writes ./out only
          python make_pdf.py 1425600095 --apply         upload and attach
          python make_pdf.py 1425600095 --apply --keep-existing
          python make_pdf.py 1425600095 --all-fields    print blanks too
          python make_pdf.py 1425600095 --profile brief force a profile
          python make_pdf.py --mock fixtures/mock_brief_linked.json

     Nothing is written to Pipefy without --apply.
'''
import argparse
import configparser
import json
import os
import sys

import my_funcs
import my_brief
import my_layout
import my_pdf
import my_pipefy

HERE = os.path.dirname(os.path.abspath(__file__))

_config = configparser.ConfigParser()
_config.read(os.path.join(HERE, "segredo.ini"))

S_OUT_DIR = _config.get("Output", "out_dir", fallback=os.path.join(HERE, "out"))


def fn_banner(stamp, b_apply=False, s_card_id="", s_profile_key=""):
     '''
          Say plainly what is about to happen, and to which tenant.
     '''
     try:
          d_me, n_status = my_pipefy.fn_whoami(stamp=stamp)
          print("=" * 74)
          print("  token   : %s" % (d_me.get("name") if n_status == 200 else "REJECTED"))
          print("  from    : %s" % my_pipefy.S_TOKEN_SOURCE)
          print("  card    : %s" % (s_card_id or "-"))
          print("  profile : %s" % (s_profile_key or "detect from the card's pipe"))
          print("  mode    : %s" % ("APPLY - WILL UPLOAD AND ATTACH" if b_apply
                                    else "DRY RUN - renders locally, writes nothing"))
          print("=" * 74)
          return n_status
     except Exception:
          return 500


def fn_write_local(stamp, o_pdf_bytes=b"", s_filename="", s_out_dir="") -> str:
     '''
          Write the PDF next to the repo so it can be opened and checked.
          Returns the path, or "".
     '''
     try:
          s_dir = s_out_dir or S_OUT_DIR
          os.makedirs(s_dir, exist_ok=True)
          s_path = os.path.join(s_dir, s_filename or "Brief.pdf")
          with open(s_path, "wb") as o_file:
               o_file.write(o_pdf_bytes)
          return s_path
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp=stamp,
                          txt=f"Could not write the PDF locally at line {e_traceback.tb_lineno}",
                          d_details={"error": str(e), "filename": s_filename})
          return ""


def fn_run_mock(stamp, s_fixture_path="", s_out_dir="", b_all_fields=False) -> int:
     '''
          Render from a fixture — no token, no network. This is how a layout
          change gets checked. Returns a process exit code.
     '''
     try:
          with open(s_fixture_path, "r", encoding="utf-8") as o_file:
               d_fixture = json.load(o_file)

          o_doc = my_layout.fn_profile_for_key(s_key=d_fixture.get("profile", ""))
          if not o_doc:
               o_doc = my_layout.fn_profile_for_pipe(
                    s_pipe_id=str((d_fixture.get("card", {}).get("pipe") or {}).get("id") or ""))
          if not o_doc:
               print("Fixture does not name a known profile or pipe.")
               return 2

          d_model, n_status = my_brief.fn_build_doc_model(
               stamp=stamp, o_doc=o_doc, d_card=d_fixture.get("card"),
               d_campaign_record=d_fixture.get("campaign_record"),
               d_pipe=d_fixture.get("pipe"), d_table=d_fixture.get("table"),
               b_all_fields=b_all_fields)
          if n_status != 200:
               print(f"Doc model build returned {n_status}.")
               return 1

          o_pdf_bytes, n_status = my_pdf.fn_render_pdf(stamp=stamp, d_model=d_model)
          if n_status != 200:
               print(f"Render returned {n_status}.")
               return 1

          s_path = fn_write_local(stamp=stamp, o_pdf_bytes=o_pdf_bytes,
                                  s_filename=d_model.get("filename"), s_out_dir=s_out_dir)
          print(f"  document  : {d_model.get('doc_title')}")
          print(f"  sections  : {len(d_model.get('sections') or [])}")
          print(f"  bytes     : {len(o_pdf_bytes)}")
          print(f"  written   : {s_path}")
          return 0
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          print(f"Mock render failed at line {e_traceback.tb_lineno}: {e}")
          return 1


def fn_main() -> int:
     '''
          Parse the arguments and run. Returns a process exit code:
          0 fine, 1 failed, 2 bad usage.
     '''
     try:
          o_parser = argparse.ArgumentParser(
               description="Render an MTN brief PDF from a Pipefy card.")
          o_parser.add_argument("card_id", nargs="?", default="",
                                help="Pipefy card id")
          o_parser.add_argument("--apply", action="store_true",
                                help="upload and attach to the card (default: dry run)")
          o_parser.add_argument("--keep-existing", action="store_true",
                                help="append alongside files already on the field")
          o_parser.add_argument("--all-fields", action="store_true",
                                help="print blank fields as 'Not provided'")
          o_parser.add_argument("--profile", default="",
                                choices=sorted(my_layout.D_PROFILE_BY_KEY) + [""],
                                help="force a profile instead of detecting it")
          o_parser.add_argument("--out", default="", help="output directory")
          o_parser.add_argument("--mock", default="",
                                help="render from a fixture JSON, no API calls")
          o_parser.add_argument("--quiet-log", action="store_true",
                                help="print log lines instead of sending to Papertrail")
          d_args = o_parser.parse_args()

          stamp = my_funcs.fn_build_stamp(
               s_card_id=d_args.card_id,
               s_mode="PrintOnly" if d_args.quiet_log else "")

          if d_args.mock:
               return fn_run_mock(stamp=stamp, s_fixture_path=d_args.mock,
                                  s_out_dir=d_args.out, b_all_fields=d_args.all_fields)

          if not d_args.card_id:
               o_parser.print_help()
               return 2

          n_status = fn_banner(stamp=stamp, b_apply=d_args.apply,
                               s_card_id=d_args.card_id, s_profile_key=d_args.profile)
          if n_status != 200:
               print(f"Token from {my_pipefy.S_TOKEN_SOURCE} was rejected or missing.")
               print("Set [Pipefy] token in segredo.ini, or MTN_PIPEFY_TOKEN / "
                     "PIPEFY_ACCESS_TOKEN in the environment or a .env above the repo.")
               return 1

          d_result, n_status = my_brief.fn_generate_brief(
               stamp=stamp, s_card_id=d_args.card_id, s_profile_key=d_args.profile,
               b_apply=d_args.apply, b_keep_existing=d_args.keep_existing,
               b_all_fields=d_args.all_fields)

          if n_status not in (200, 202):
               print(f"  FAILED with {n_status}: {d_result.get('error')}")
               return 1

          o_pdf_bytes = d_result.pop("pdf_bytes", b"")
          s_path = fn_write_local(stamp=stamp, o_pdf_bytes=o_pdf_bytes,
                                  s_filename=d_result.get("filename"),
                                  s_out_dir=d_args.out)
          print(f"  document  : {d_result.get('document')}")
          print(f"  campaign  : {'linked' if d_result.get('campaign_linked') else 'none'}"
                f" ({d_result.get('campaign_route')})")
          print(f"  sections  : {d_result.get('sections')}")
          print(f"  written   : {s_path}")
          if d_args.apply:
               print(f"  attached  : {d_result.get('attach_field')} on card "
                     f"{d_result.get('card_id')}")
               print(f"  replaced  : {d_result.get('replaced_files', 0)} existing file(s)")
               print(f"  verified  : {d_result.get('verified')}")
               if not d_result.get("verified"):
                    print("  The read-back could not confirm the file. Check the card.")
                    return 1
          else:
               print("  Nothing was written to Pipefy. Re-run with --apply to attach.")
          return 0

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          print(f"make_pdf failed at line {e_traceback.tb_lineno}: {e}")
          return 1


if __name__ == "__main__":
     sys.exit(fn_main())

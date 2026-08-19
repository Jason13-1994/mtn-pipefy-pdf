'''
     tests/test_long_token_wrap.py — guards FIX-01's long-token wrap guarantee.

     FIX-01 made my_pdf.fn_styles() state splitLongWords=True explicitly on the four
     value-bearing ParagraphStyle keys (value, value_b, bullet, meta_v) instead of relying
     on reportlab's own unstated ParagraphStyle class default. This file locks that
     guarantee down with two layers: a cheap unit-level assertion that a real 96-character
     unbroken token wraps within the real inline-table column width, and a render-level
     smoke assertion that a full fn_render_pdf() call with the same token embedded in an
     inline and a block item still returns (pdf_bytes, 200) with no exception.

     Naming convention note: pytest's own collection requires test functions to be named
     test_*, which is this repo's one documented exception to the fn_ prefix rule — do not
     rename these to fn_test_..., that would silently produce "0 tests collected" instead
     of a failure. Test functions use bare assert and never the (data, status_code) tuple
     contract: a test either passes or raises AssertionError, there is no caller to hand a
     status code back to.

     D-04 residual, carried forward unchanged: fn_page_header()/fn_cover_header()
     (my_pdf.py:194-236) draw the doc title and job/campaign name via
     o_canvas.drawRightString(...) — canvas primitives, not Paragraph — with only a [:70]
     character-count truncation and no width-based wrap. splitLongWords only applies to
     Paragraph objects, so this narrow path is NOT covered by this file. These draw a
     Pipefy short_text field (job/campaign name), realistically never a URL or UUID. Not in
     scope for this phase, no code change proposed here.
'''
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph

import my_pdf


def test_long_token_wraps_within_inline_column():
     '''
          A 96-character unbroken token (no whitespace) run through the real
          d_styles["value"] style, wrapped at the real inline-table column width
          (my_pdf.CONTENT_W - my_pdf.LABEL_COL_W - 8 * my_pdf.mm, 306.14pt at A4), must
          produce wrapped lines that are all within that column width.
     '''
     s_token = "a1b2c3d4e5f6" * 8   # 96 chars, no whitespace
     d_styles = my_pdf.fn_styles()
     f_col_w = my_pdf.CONTENT_W - my_pdf.LABEL_COL_W - 8 * my_pdf.mm
     o_para = Paragraph(my_pdf.fn_escape(s_token), d_styles["value"])
     o_para.wrap(f_col_w, 1000)
     assert len(o_para.blPara.lines) > 0
     for o_line in o_para.blPara.lines:
          s_text = "".join(x if isinstance(x, str) else str(x) for x in o_line[1])
          f_line_w = stringWidth(s_text, "Helvetica", 9.5)
          assert f_line_w <= f_col_w + 0.5   # +0.5pt float-rounding tolerance


def test_long_token_full_render_does_not_raise():
     '''
          The same 96-character token embedded as an "inline" item's value AND a
          "block" item's value in a minimal but doc-model-contract-complete dict, passed
          to fn_render_pdf(), must return (pdf_bytes, 200) with non-zero bytes and no
          exception.
     '''
     s_token = "a1b2c3d4e5f6" * 8   # 96 chars, no whitespace
     d_model = {
          "doc_title": "Job Brief",
          "pipe_label": "Campaign Briefing",
          "title": "Long token render smoke test",
          "subtitle": "",
          "meta": [("Card ID", "0")],
          "highlight": {},
          "sections": [
               {
                    "title": "Section",
                    "note": "",
                    "items": [
                         {"kind": "inline", "label": "Tracking ID", "value": s_token,
                          "note": ""},
                         {"kind": "block", "label": "Long text", "value": s_token,
                          "note": ""},
                    ],
               },
          ],
          "footer_ref": "Card #0",
          "generated": "18 Aug 2026 09:14 SAST",
          "source_url": "",
     }
     stamp = {"time": 0, "card_id": "test", "Mode": "PrintOnly"}
     o_bytes, n_status = my_pdf.fn_render_pdf(stamp=stamp, d_model=d_model)
     assert n_status == 200
     assert len(o_bytes) > 0

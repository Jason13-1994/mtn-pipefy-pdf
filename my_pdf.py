'''
     my_pdf.py — MTN brand constants and the reportlab renderer.

     This module knows NOTHING about Pipefy. Feed it the doc model my_brief.py
     produces and it returns PDF bytes. That separation is what lets the layout
     be tested from a fixture with no token and no network.

     DOC MODEL
     ---------
     {
       "doc_title":  "Job Brief",
       "pipe_label": "Campaign Briefing",
       "title":      "Uni Activations",              # cover H1
       "subtitle":   "Above the line · Uganda · Tier 1",
       "meta":       [("Card ID", "1425600095"), ...],   # cover key/value grid
       "highlight":  {"label": "...", "value": "..."},   # optional cover block
       "sections":   [{"title": "...", "note": "...", "items": [...]}],
       "footer_ref": "Card #1425600095",
       "generated":  "18 Aug 2026 09:14 SAST",
       "source_url": "https://app.pipefy.com/open-cards/...",
     }

     item kinds:
       inline -> label/value row in a two-column table (short answers)
       block  -> label above, full-width paragraph below (long text)
       list   -> label above, bulleted values (multi-selects, attachments)
'''
import io
import os
import sys
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, KeepTogether,
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

import my_funcs

HERE = os.path.dirname(os.path.abspath(__file__))
S_ASSETS_DIR = os.path.join(HERE, "assets")


'''
     *****************************************************
           MTN BRAND
     *****************************************************
'''

# Core palette — MTN yellow and black, plus a small neutral ramp for labels,
# rules and secondary text. Do not add colours without a reason: the point of
# the layout is that it looks like MTN, not like a report template that happens
# to be yellow.
MTN_YELLOW = HexColor("#FFCB05")
MTN_BLACK = HexColor("#000000")
INK = HexColor("#111111")      # body text
LABEL = HexColor("#5A5A5A")    # field labels, meta text
MUTED = HexColor("#8A8A8A")    # footer, "Not provided"
RULE = HexColor("#DCDCDC")     # hairlines between rows
BAND_BG = HexColor("#F6F6F6")  # zebra / block background

# MTN Brighter Sans is not redistributable, so the document sets in the
# PDF-standard Helvetica family. Drop the brand TTFs into assets/fonts/ and
# register them here — nothing else in the layout changes.
FONT = "Helvetica"
FONT_B = "Helvetica-Bold"
FONT_I = "Helvetica-Oblique"

S_LOGO_TRANSPARENT = os.path.join(S_ASSETS_DIR, "mtn_logo_transparent.png")
S_LOGO_TILE = os.path.join(S_ASSETS_DIR, "mtn_logo.png")
S_CONFIDENTIALITY = "Confidential - MTN"

PAGE_W, PAGE_H = A4
MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R
COVER_BAND_H = 46 * mm
PAGE_BAND_H = 20 * mm
FOOTER_H = 16 * mm
LABEL_COL_W = 58 * mm


def fn_logo_for_yellow():
     '''
          Logo to place ON the yellow band. Returns "" when neither file exists.
     '''
     try:
          for s_path in (S_LOGO_TRANSPARENT, S_LOGO_TILE):
               if os.path.exists(s_path):
                    return s_path
          return ""
     except Exception:
          return ""


def fn_logo_for_white():
     '''
          Logo to place on a white page header. Returns "".
     '''
     try:
          for s_path in (S_LOGO_TILE, S_LOGO_TRANSPARENT):
               if os.path.exists(s_path):
                    return s_path
          return ""
     except Exception:
          return ""


'''
     *****************************************************
           STYLES AND PAGE FURNITURE
     *****************************************************
'''


def fn_styles() -> dict:
     '''
          Paragraph styles used across the document.
     '''
     try:
          d_styles = {}
          d_styles["title"] = ParagraphStyle("title", fontName=FONT_B, fontSize=23,
                                             leading=27, textColor=MTN_BLACK, spaceAfter=2)
          d_styles["subtitle"] = ParagraphStyle("subtitle", fontName=FONT, fontSize=11,
                                                leading=15, textColor=LABEL)
          d_styles["section"] = ParagraphStyle("section", fontName=FONT_B, fontSize=11.5,
                                               leading=14, textColor=MTN_BLACK)
          d_styles["label"] = ParagraphStyle("label", fontName=FONT_B, fontSize=8.5,
                                             leading=11.5, textColor=LABEL)

          # reportlab's own ParagraphStyle class default already makes long-word wrap
          # guaranteed (the literal comment in reportlab's own source, venv/Lib/site-
          # packages/reportlab/lib/styles.py:143, is: 'splitLongWords':1). Stated explicitly
          # on the four value-bearing styles below so a long unbroken token (URL, UUID,
          # tracking id) is guaranteed to wrap within its column as a property of THIS code,
          # not an unstated library default a future reportlab version could change.
          d_styles["value"] = ParagraphStyle("value", fontName=FONT, fontSize=9.5,
                                             leading=13, textColor=INK,
                                             splitLongWords=True)
          d_styles["value_b"] = ParagraphStyle("value_b", fontName=FONT, fontSize=9.5,
                                               leading=14, textColor=INK, spaceBefore=1,
                                               splitLongWords=True)
          d_styles["bullet"] = ParagraphStyle("bullet", fontName=FONT, fontSize=9.5,
                                              leading=13.5, textColor=INK, leftIndent=9,
                                              bulletIndent=0, spaceBefore=0.5,
                                              splitLongWords=True)
          d_styles["empty"] = ParagraphStyle("empty", fontName=FONT_I, fontSize=9,
                                             leading=13, textColor=MUTED)
          d_styles["meta_k"] = ParagraphStyle("meta_k", fontName=FONT_B, fontSize=7.5,
                                              leading=10, textColor=LABEL)
          d_styles["meta_v"] = ParagraphStyle("meta_v", fontName=FONT, fontSize=9.5,
                                              leading=12, textColor=INK,
                                              splitLongWords=True)
          d_styles["cover_note"] = ParagraphStyle("cover_note", fontName=FONT, fontSize=8,
                                                  leading=11, textColor=MUTED)
          d_styles["sec_note"] = ParagraphStyle("sec_note", fontName=FONT_I, fontSize=8,
                                                leading=11, textColor=LABEL,
                                                leftIndent=5 * mm)
          d_styles["item_note"] = ParagraphStyle("item_note", fontName=FONT_I, fontSize=7.5,
                                                 leading=10, textColor=MUTED)
          return d_styles
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp={}, txt=f"fn_styles failed at line "
                          f"{e_traceback.tb_lineno}", d_details={"error": str(e)})
          return {}


def fn_escape(s_text="") -> str:
     '''
          Escape for reportlab Paragraph markup, keeping author line breaks.
     '''
     try:
          if s_text is None:
               return ""
          return (escape(str(s_text)).replace("\r\n", "\n").replace("\r", "\n")
                  .replace("\n", "<br/>"))
     except Exception:
          return ""


def fn_draw_logo(o_canvas, s_path="", f_x=0, f_y=0, f_max_w=0, f_max_h=0):
     '''
          Draw a logo scaled into a box, vertically centred. Silent no-op when
          the file is missing — a missing logo must not stop a brief.
     '''
     try:
          if not s_path:
               return
          o_image = ImageReader(s_path)
          i_width, i_height = o_image.getSize()
          f_scale = min(f_max_w / float(i_width), f_max_h / float(i_height))
          o_canvas.drawImage(o_image, f_x, f_y + (f_max_h - i_height * f_scale) / 2.0,
                             width=i_width * f_scale, height=i_height * f_scale,
                             mask="auto")
     except Exception:
          return


def fn_cover_header(o_canvas, o_doc):
     '''
          Yellow masthead band on the cover page.
     '''
     try:
          o_canvas.saveState()
          o_canvas.setFillColor(MTN_YELLOW)
          o_canvas.rect(0, PAGE_H - COVER_BAND_H, PAGE_W, COVER_BAND_H, stroke=0, fill=1)
          o_canvas.setFillColor(MTN_BLACK)
          o_canvas.rect(0, PAGE_H - COVER_BAND_H - 2.2 * mm, PAGE_W, 2.2 * mm,
                        stroke=0, fill=1)
          fn_draw_logo(o_canvas, fn_logo_for_yellow(), MARGIN_L,
                       PAGE_H - COVER_BAND_H + 9 * mm, 38 * mm, COVER_BAND_H - 18 * mm)
          o_canvas.setFillColor(MTN_BLACK)
          o_canvas.setFont(FONT_B, 13)
          o_canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - COVER_BAND_H + 20 * mm,
                                   str(o_doc._d_model.get("doc_title") or "Brief").upper())
          o_canvas.setFont(FONT, 8)
          o_canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - COVER_BAND_H + 14 * mm,
                                   "Generated from Pipefy")
          o_canvas.restoreState()
     except Exception:
          return


def fn_page_header(o_canvas, o_doc):
     '''
          Slim running header on every page after the cover.
     '''
     try:
          o_canvas.saveState()
          fn_draw_logo(o_canvas, fn_logo_for_white(), MARGIN_L,
                       PAGE_H - PAGE_BAND_H - 2 * mm, 22 * mm, 12 * mm)
          o_canvas.setFillColor(LABEL)
          o_canvas.setFont(FONT, 8)
          o_canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - PAGE_BAND_H + 1.5 * mm,
                                   str(o_doc._d_model.get("title", ""))[:70])
          o_canvas.setFillColor(MTN_YELLOW)
          o_canvas.rect(MARGIN_L, PAGE_H - PAGE_BAND_H - 4.5 * mm, CONTENT_W, 1.6 * mm,
                        stroke=0, fill=1)
          o_canvas.restoreState()
     except Exception:
          return


class NumberedCanvas(pdfcanvas.Canvas):
     '''
          Two-pass canvas so the footer can print "Page X of Y".

          NOTE ON ERROR HANDLING: showPage() and save() are deliberately NOT
          wrapped, unlike every other function in this repo. They are reportlab
          machinery, and swallowing a failure here would hand back a truncated
          PDF that looks like a success. Letting it propagate into
          fn_render_pdf()'s handler turns it into a clean 500 and no attachment.
          _fn_footer IS wrapped — a footer is not worth failing a brief over.
     '''

     def __init__(self, *args, **kwargs):
          self._d_model = kwargs.pop("d_model", {})
          pdfcanvas.Canvas.__init__(self, *args, **kwargs)
          self._l_saved = []

     def showPage(self):
          self._l_saved.append(dict(self.__dict__))
          self._startPage()

     def save(self):
          i_total = len(self._l_saved)
          for d_state in self._l_saved:
               self.__dict__.update(d_state)
               self._fn_footer(i_total)
               pdfcanvas.Canvas.showPage(self)
          pdfcanvas.Canvas.save(self)

     def _fn_footer(self, i_total=0):
          try:
               self.saveState()
               f_y = FOOTER_H
               self.setFillColor(RULE)
               self.rect(MARGIN_L, f_y + 4 * mm, CONTENT_W, 0.4, stroke=0, fill=1)
               self.setFont(FONT, 7.2)
               self.setFillColor(MUTED)
               s_left = "MTN | %s  |  %s" % (self._d_model.get("pipe_label") or "Pipefy",
                                             self._d_model.get("footer_ref", ""))
               self.drawString(MARGIN_L, f_y, s_left)
               self.drawCentredString(PAGE_W / 2.0, f_y, S_CONFIDENTIALITY)
               self.drawRightString(PAGE_W - MARGIN_R, f_y,
                                    "Page %d of %d" % (self.getPageNumber(), i_total))
               self.restoreState()
          except Exception:
               return


class BriefDoc(BaseDocTemplate):
     '''
          Cover template then body template, both A4 portrait.
     '''

     def __init__(self, o_target, d_model=None, **kwargs):
          self._d_model = d_model or {}
          BaseDocTemplate.__init__(
               self, o_target, pagesize=A4,
               leftMargin=MARGIN_L, rightMargin=MARGIN_R, topMargin=0, bottomMargin=0,
               title="%s - %s" % (self._d_model.get("doc_title") or "Brief",
                                  self._d_model.get("title", "")),
               author="MTN %s (Pipefy)" % (self._d_model.get("pipe_label") or ""),
               subject=self._d_model.get("doc_title") or "Brief", **kwargs)
          o_cover_frame = Frame(MARGIN_L, FOOTER_H + 8 * mm, CONTENT_W,
                                PAGE_H - COVER_BAND_H - 12 * mm - FOOTER_H - 8 * mm,
                                id="cover", leftPadding=0, rightPadding=0,
                                topPadding=0, bottomPadding=0)
          o_body_frame = Frame(MARGIN_L, FOOTER_H + 8 * mm, CONTENT_W,
                               PAGE_H - PAGE_BAND_H - 8 * mm - FOOTER_H - 8 * mm,
                               id="body", leftPadding=0, rightPadding=0,
                               topPadding=0, bottomPadding=0)
          self.addPageTemplates([
               PageTemplate(id="cover", frames=[o_cover_frame], onPage=fn_cover_header),
               PageTemplate(id="body", frames=[o_body_frame], onPage=fn_page_header),
          ])


'''
     *****************************************************
           FLOWABLES
     *****************************************************
'''


def fn_section_bar(s_title="", d_styles=None):
     '''
          Yellow section bar with a black rule under it.
     '''
     try:
          o_table = Table([[Paragraph(fn_escape(s_title).upper(), d_styles["section"])]],
                          colWidths=[CONTENT_W], rowHeights=[9.5 * mm])
          o_table.setStyle(TableStyle([
               ("BACKGROUND", (0, 0), (-1, -1), MTN_YELLOW),
               ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
               ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
               ("LINEBELOW", (0, 0), (-1, -1), 1.4, MTN_BLACK),
          ]))
          return o_table
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp={}, txt=f"fn_section_bar failed at line "
                          f"{e_traceback.tb_lineno}", d_details={"error": str(e)})
          return Spacer(1, 0)


def fn_inline_table(l_rows=None, d_styles=None):
     '''
          l_rows: list of (label, value, note) -> zebra-striped 2-column table.
     '''
     try:
          l_data = []
          for s_label, s_value, s_note in (l_rows or []):
               if s_value:
                    l_cell = [Paragraph(fn_escape(s_value), d_styles["value"])]
               else:
                    l_cell = [Paragraph("Not provided", d_styles["empty"])]
               if s_note:
                    l_cell.append(Paragraph(fn_escape(s_note), d_styles["item_note"]))
               o_inner = Table([[o_part] for o_part in l_cell],
                               colWidths=[CONTENT_W - LABEL_COL_W - 8 * mm])
               o_inner.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
               ]))
               l_data.append([Paragraph(fn_escape(s_label), d_styles["label"]), o_inner])

          o_table = Table(l_data, colWidths=[LABEL_COL_W, CONTENT_W - LABEL_COL_W],
                          hAlign="LEFT")
          l_style = [
               ("VALIGN", (0, 0), (-1, -1), "TOP"),
               ("TOPPADDING", (0, 0), (-1, -1), 3.2),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
               ("LEFTPADDING", (0, 0), (0, -1), 5 * mm),
               ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
               ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
          ]
          for i_row in range(len(l_data)):
               if i_row % 2 == 1:
                    l_style.append(("BACKGROUND", (0, i_row), (-1, i_row), BAND_BG))
          o_table.setStyle(TableStyle(l_style))
          return o_table
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp={}, txt=f"fn_inline_table failed at line "
                          f"{e_traceback.tb_lineno}", d_details={"error": str(e)})
          return Spacer(1, 0)


def fn_block(s_label="", s_value="", s_note="", d_styles=None):
     '''
          Full-width long-text block with a yellow rule down the left edge.
     '''
     try:
          l_parts = [Paragraph(fn_escape(s_label).upper(), d_styles["label"]),
                     Spacer(1, 1.4 * mm)]
          if s_value:
               l_parts.append(Paragraph(fn_escape(s_value), d_styles["value_b"]))
          else:
               l_parts.append(Paragraph("Not provided", d_styles["empty"]))
          if s_note:
               l_parts.append(Spacer(1, 1 * mm))
               l_parts.append(Paragraph(fn_escape(s_note), d_styles["item_note"]))

          o_inner = Table([[o_part] for o_part in l_parts], colWidths=[CONTENT_W - 10 * mm],
                          hAlign="LEFT")
          o_inner.setStyle(TableStyle([
               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
          ]))
          o_outer = Table([[o_inner]], colWidths=[CONTENT_W], hAlign="LEFT")
          o_outer.setStyle(TableStyle([
               ("BACKGROUND", (0, 0), (-1, -1), BAND_BG),
               ("LINEBEFORE", (0, 0), (0, -1), 2.2, MTN_YELLOW),
               ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
               ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
               ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
          ]))
          return o_outer
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp={}, txt=f"fn_block failed at line "
                          f"{e_traceback.tb_lineno}", d_details={"error": str(e)})
          return Spacer(1, 0)


def fn_list_block(s_label="", l_values=None, s_note="", d_styles=None):
     '''
          Label above a bulleted list — multi-selects, checklists, attachments.
     '''
     try:
          l_parts = [Paragraph(fn_escape(s_label).upper(), d_styles["label"]),
                     Spacer(1, 1.2 * mm)]
          if l_values:
               for s_value in l_values:
                    l_parts.append(Paragraph(fn_escape(s_value), d_styles["bullet"],
                                             bulletText="•"))
          else:
               l_parts.append(Paragraph("Not provided", d_styles["empty"]))
          if s_note:
               l_parts.append(Spacer(1, 0.8 * mm))
               l_parts.append(Paragraph(fn_escape(s_note), d_styles["item_note"]))

          o_table = Table([[o_part] for o_part in l_parts], colWidths=[CONTENT_W - 5 * mm],
                          hAlign="LEFT")
          o_table.setStyle(TableStyle([
               ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
               ("RIGHTPADDING", (0, 0), (-1, -1), 0),
               ("TOPPADDING", (0, 0), (-1, -1), 0),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
          ]))
          return KeepTogether([o_table, Spacer(1, 3 * mm)])
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp={}, txt=f"fn_list_block failed at line "
                          f"{e_traceback.tb_lineno}", d_details={"error": str(e)})
          return Spacer(1, 0)


def fn_cover_meta(l_meta=None, d_styles=None):
     '''
          Cover key/value grid, two per row.
     '''
     try:
          if not l_meta:
               return Spacer(1, 0)
          l_cells = []
          for s_key, s_value in l_meta:
               o_inner = Table([[Paragraph(fn_escape(s_key).upper(), d_styles["meta_k"])],
                                [Paragraph(fn_escape(s_value) or "-", d_styles["meta_v"])]],
                               colWidths=[(CONTENT_W / 2.0) - 6 * mm])
               o_inner.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0.6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
               ]))
               l_cells.append(o_inner)
          l_rows = []
          for i_index in range(0, len(l_cells), 2):
               l_pair = l_cells[i_index:i_index + 2]
               if len(l_pair) == 1:
                    l_pair.append("")
               l_rows.append(l_pair)
          o_table = Table(l_rows, colWidths=[CONTENT_W / 2.0] * 2, hAlign="LEFT")
          o_table.setStyle(TableStyle([
               ("VALIGN", (0, 0), (-1, -1), "TOP"),
               ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
               ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
               ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
               ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
               ("LINEAFTER", (0, 0), (0, -1), 0.4, RULE),
               ("LINEABOVE", (0, 0), (-1, 0), 1.6, MTN_BLACK),
          ]))
          return o_table
     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(stamp={}, txt=f"fn_cover_meta failed at line "
                          f"{e_traceback.tb_lineno}", d_details={"error": str(e)})
          return Spacer(1, 0)


'''
     *****************************************************
           RENDER
     *****************************************************
'''


def fn_render_pdf(stamp, d_model=None) -> tuple:
     '''
          Doc model -> PDF bytes. Returns (o_pdf_bytes, n_status).
     '''
     try:
          d_model = d_model or {}
          d_styles = fn_styles()
          l_story = []

          # ---- cover ----
          l_story.append(Spacer(1, 8 * mm))
          l_story.append(Paragraph(fn_escape(d_model.get("title") or "Untitled"),
                                   d_styles["title"]))
          if d_model.get("subtitle"):
               l_story.append(Spacer(1, 1 * mm))
               l_story.append(Paragraph(fn_escape(d_model["subtitle"]),
                                        d_styles["subtitle"]))
          l_story.append(Spacer(1, 7 * mm))
          l_story.append(fn_cover_meta(l_meta=d_model.get("meta") or [],
                                       d_styles=d_styles))
          d_highlight = d_model.get("highlight") or {}
          if d_highlight.get("value"):
               l_story.append(Spacer(1, 6 * mm))
               l_story.append(fn_block(s_label=d_highlight.get("label", ""),
                                       s_value=d_highlight["value"], d_styles=d_styles))
          l_story.append(Spacer(1, 5 * mm))
          s_note = ("Generated %s from the MTN %s board in Pipefy. This document is a "
                    "point-in-time snapshot of the card at the time of generation."
                    % (d_model.get("generated") or "", d_model.get("pipe_label") or ""))
          l_story.append(Paragraph(fn_escape(s_note), d_styles["cover_note"]))
          if d_model.get("source_url"):
               l_story.append(Spacer(1, 1.5 * mm))
               l_story.append(Paragraph(fn_escape("Source card: " + d_model["source_url"]),
                                        d_styles["cover_note"]))

          # ---- body ----
          l_story.append(NextPageTemplate("body"))
          b_first_section = True
          for d_section in d_model.get("sections") or []:
               l_items = d_section.get("items") or []
               if not l_items and not d_section.get("note"):
                    continue
               if b_first_section:
                    l_story.append(PageBreak())
                    b_first_section = False
               else:
                    l_story.append(Spacer(1, 6 * mm))
               l_story.append(CondPageBreak(48 * mm))
               l_story.append(fn_section_bar(s_title=d_section.get("title") or "",
                                             d_styles=d_styles))
               l_story.append(Spacer(1, 3 * mm))
               if d_section.get("note"):
                    l_story.append(Paragraph(fn_escape(d_section["note"]),
                                             d_styles["sec_note"]))
                    l_story.append(Spacer(1, 3 * mm))

               # Group consecutive inline items into one table so the rules line up.
               l_buffer = []
               for d_item in l_items:
                    s_kind = d_item.get("kind", "inline")
                    if s_kind == "inline":
                         l_buffer.append((d_item.get("label", ""), d_item.get("value", ""),
                                          d_item.get("note", "")))
                         continue
                    if l_buffer:
                         l_story.append(fn_inline_table(l_rows=l_buffer, d_styles=d_styles))
                         l_story.append(Spacer(1, 3.5 * mm))
                         l_buffer = []
                    if s_kind == "list":
                         l_story.append(fn_list_block(s_label=d_item.get("label", ""),
                                                      l_values=d_item.get("values") or [],
                                                      s_note=d_item.get("note", ""),
                                                      d_styles=d_styles))
                    else:
                         l_story.append(fn_block(s_label=d_item.get("label", ""),
                                                 s_value=d_item.get("value", ""),
                                                 s_note=d_item.get("note", ""),
                                                 d_styles=d_styles))
                         l_story.append(Spacer(1, 3 * mm))
               if l_buffer:
                    l_story.append(fn_inline_table(l_rows=l_buffer, d_styles=d_styles))

          o_buffer = io.BytesIO()
          o_document = BriefDoc(o_buffer, d_model=d_model)
          o_document.build(
               l_story,
               canvasmaker=lambda *a, **k: NumberedCanvas(*a, d_model=d_model, **k),
          )
          o_pdf_bytes = o_buffer.getvalue()
          if not o_pdf_bytes:
               my_funcs.fn_log(stamp=stamp, txt="PDF render produced zero bytes",
                               d_details={"title": d_model.get("title")})
               return b"", 500
          return o_pdf_bytes, 200

     except Exception as e:
          e_type, e_object, e_traceback = sys.exc_info()
          my_funcs.fn_log(
               stamp=stamp,
               txt=f"PDF render failed at line {e_traceback.tb_lineno}",
               d_details={"error": str(e), "title": (d_model or {}).get("title"),
                          "sections": len((d_model or {}).get("sections") or [])},
          )
          return b"", 500

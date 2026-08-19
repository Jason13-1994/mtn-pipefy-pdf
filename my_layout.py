'''
     my_layout.py — WHAT GOES ON EACH PDF.

     This is the file you edit. Everything else is machinery.

     ADDING A FIELD TO A DOCUMENT IS ONE LINE:

          Field("new_field_id"),

     The label comes off the live Pipefy form at run time, so a wording change
     in Pipefy needs no code change. The ALLOWLIST is pinned here on purpose —
     a field that nobody has added to this file does not appear in a document.
     That is what stops a stray form field turning up in a brief an external
     agency reads. Run check_drift.py to be told when the form has grown a
     field this file does not mention.

     Two documents:
          Campaign Planning  307284211 -> "Campaign Brief" -> campaign_attached
          Campaign Briefing  307284210 -> "Job Brief"      -> brief_attached

     Agency Workflow 307284207 deliberately has NO profile. Agency cards receive
     the Job Brief through the existing fan-out automation, which copies
     brief_attached from the briefing card on the move to Brief Submitted.
'''

CAMPAIGN_TABLE_ID = "mOUzRnnK"          # Campaign Planning DB (URL id 307284208)


'''
     *****************************************************
           VOCABULARY
     *****************************************************
'''


class Field(object):
     '''
          One field on the document.

          s_field_id   Pipefy field id. The only required argument.
                       "@id", "@phase", "@assignees", "@campaign_title" and
                       "@current_date" are resolver-supplied pseudo-fields.
          s_label      Override the live form label. Leave blank to track Pipefy.
          s_source     "card"     — this card only (default)
                       "campaign" — the linked campaign record only
                       "auto"     — the campaign record if one is linked,
                                    otherwise this card. This is the
                                    linked-vs-standalone brief switch.
          b_always     Print "Not provided" when blank instead of skipping the
                       row. Use where the absence is itself information.
          s_render     Force "inline" | "block" | "list". Blank = decide from
                       the Pipefy field type.
          s_note       Small grey line printed under the value.
     '''

     def __init__(self, s_field_id, s_label="", s_source="card", b_always=False,
                  s_render="", s_note=""):
          self.s_field_id = s_field_id
          self.s_label = s_label
          self.s_source = s_source
          self.b_always = b_always
          self.s_render = s_render
          self.s_note = s_note


class OneOf(object):
     '''
          Collapse several mutually-exclusive fields into one row — first
          populated wins. MTN's forms carry fifteen division selects of which a
          card fills one; without this the document prints fourteen empty rows.
     '''

     def __init__(self, s_label, l_field_ids, s_source="card", b_always=False):
          self.s_label = s_label
          self.l_field_ids = list(l_field_ids)
          self.s_source = s_source
          self.b_always = b_always
          self.s_render = "inline"
          self.s_note = ""


class Section(object):
     '''
          A yellow section bar and the items under it. A section whose items are
          all empty is dropped from the document.
     '''

     def __init__(self, s_title, l_items, s_note=""):
          self.s_title = s_title
          self.l_items = list(l_items)
          self.s_note = s_note


class Doc(object):
     '''
          One document profile. See the two instances below.
     '''

     def __init__(self, s_key="", s_pipe_id="", s_pipe_label="", s_doc_title="",
                  s_attach_field="", s_name_field="", s_filename_template="",
                  s_trigger_phase_id="", s_trigger_phase_label="",
                  l_subtitle=None, t_highlight=None, l_meta=None,
                  l_sections=None, l_tail_sections=None,
                  d_campaign=None, set_deny=None):
          self.s_key = s_key
          self.s_pipe_id = s_pipe_id
          self.s_pipe_label = s_pipe_label
          self.s_doc_title = s_doc_title
          self.s_attach_field = s_attach_field
          self.s_name_field = s_name_field
          self.s_filename_template = s_filename_template
          self.s_trigger_phase_id = s_trigger_phase_id
          self.s_trigger_phase_label = s_trigger_phase_label
          self.l_subtitle = list(l_subtitle or [])
          self.t_highlight = t_highlight
          self.l_meta = list(l_meta or [])
          self.l_sections = list(l_sections or [])
          self.l_tail_sections = list(l_tail_sections or [])
          self.d_campaign = d_campaign or {}
          self.set_deny = set(set_deny or [])


# The fifteen division selects, shared by both forms. Same ids on both pipes.
L_DIVISION_FIELDS = [
     "uganda_division", "uganda_marketing_division", "uganda_finance_division",
     "uganda_enterprise_division", "uganda_technology_division",
     "uganda_corporate_services_division", "uganda_business_intelligence_division",
     "zambia_division", "zambia_marketing_division",
     "zambia_enterprise_business_unit_ebu", "zambia_mtn_home_division",
     "zambia_finance_division", "zambia_technology_division",
     "zambia_corporate_services",
]


'''
     *****************************************************
           CAMPAIGN BRIEF — Campaign Planning 307284211
     *****************************************************
'''

D_CAMPAIGN_BRIEF = Doc(
     s_key="campaign",
     s_pipe_id="307284211",
     s_pipe_label="Campaign Planning",
     s_doc_title="Campaign Brief",
     s_attach_field="campaign_attached",
     s_name_field="campaign_name",
     s_filename_template="Campaign Brief - {name} - {originating_opco} - {card_id}.pdf",
     s_trigger_phase_id="343906151",
     s_trigger_phase_label="Campaign Review",

     l_subtitle=[
          Field("originating_opco"),
          Field("tier"),
          Field("campaign_year"),
     ],

     t_highlight=("Campaign objective", Field("campaign_objective")),

     l_meta=[
          ("Campaign", Field("campaign_name")),
          ("Originating OpCo", Field("originating_opco")),
          ("Card ID", Field("@id")),
          ("Current phase", Field("@phase")),
          ("Go live", Field("campaign_go_live_date", b_always=True)),
          ("End date", Field("campaign_end_date", b_always=True)),
          ("Campaign budget", Field("campaign_budget", b_always=True)),
          ("Campaign owner", Field("campaign_owner")),
     ],

     l_sections=[
          Section("Campaign Information", [
               Field("campaign_name"),
               Field("originating_opco", b_always=True),
               Field("tier", b_always=True),
               OneOf("Division", L_DIVISION_FIELDS),
          ]),

          Section("Campaign Timelines", [
               Field("campaign_year"),
               Field("campaign_go_live_date", b_always=True),
               Field("campaign_end_date", b_always=True),
               Field("product_go_live_date"),
               Field("key_milestones", s_render="block"),
          ]),

          Section("Campaign Details", [
               Field("campaign_budget", b_always=True),
               Field("strategic_pillar"),
               Field("zambian_promotion_budget"),
               Field("zambian_positioning_budget"),
               Field("zambian_proposition_budget"),
               Field("ugandan_positioning_budget"),
               Field("ugandan_proposition_budget"),
               Field("campaign_objective", s_render="block"),
               Field("campaign_background", s_render="block"),
               Field("key_message", s_render="block"),
               Field("what_problem_are_we_solving_for_the_customer", s_render="block"),
               Field("target_audience"),
               Field("target_audience_other"),
               Field("target_audience_additional_information", s_render="block"),
          ]),

          Section("Campaign KPI's", [
               Field("kpi_pillar"),
               Field("kpi_pillar_other"),
               Field("awareness_kpi"),
               Field("awareness_kpi_other"),
               Field("acquisition_growth_kpi"),
               Field("acquisition_and_growth_kpi_other"),
               Field("digital_communication_kpi"),
               Field("digital_communication_kpi_other"),
               Field("brand_desire_kpi"),
               Field("brand_desire_kpi_other"),
               Field("nps_kpi"),
               Field("nps_kpi_other"),
               Field("kpi_additional_information", s_render="block"),
          ]),

          Section("Supporting Information", [
               Field("supporting_documentation"),
               Field("supporting_documents_attachment_s"),
               Field("supporting_documents_free_text_link_s", s_render="block"),
          ]),
     ],

     l_tail_sections=[
          Section("Review and approval", [
               Field("campaign_review_decision"),
               Field("reviewer"),
               Field("reviewer_comments", s_render="block"),
               Field("approval_status"),
               Field("campaign_approval_date"),
               Field("approval_authority"),
               Field("approval_notes", s_render="block"),
               Field("approval_document"),
          ]),

          # Only ever populated on a cancelled campaign. A brief for a campaign
          # that was pulled should say why it was pulled.
          Section("Cancellation", [
               Field("reason_for_cancellation"),
               Field("cancellation_date"),
               Field("stakeholder_feedback", s_render="block"),
               Field("lessons_learned", s_render="block"),
               Field("next_steps_post_cancellation"),
          ]),
     ],

     # Never render, whatever anyone adds to the form later.
     set_deny={
          "campaign_attached",                  # circular — this PDF lands there
          "approver_email",                     # internal routing
          "copy_of_zambian_promotion_budget",   # duplicate left over from form build
     },
)


'''
     *****************************************************
           JOB BRIEF — Campaign Briefing 307284210
     *****************************************************
'''

D_JOB_BRIEF = Doc(
     s_key="brief",
     s_pipe_id="307284210",
     s_pipe_label="Campaign Briefing",
     s_doc_title="Job Brief",
     s_attach_field="brief_attached",
     s_name_field="job_name",
     s_filename_template="Job Brief - {name} - {originating_opco} - {card_id}.pdf",
     s_trigger_phase_id="343906141",
     s_trigger_phase_label="Brief Review - 1st Approval",

     l_subtitle=[
          Field("brief_type"),
          Field("originating_opco", s_source="auto"),
          Field("tier", s_source="auto"),
     ],

     t_highlight=("The brief in a sentence", Field("the_brief_in_a_sentence")),

     l_meta=[
          ("Job", Field("job_name")),
          ("Brief type", Field("brief_type")),
          ("Approved campaign", Field("@campaign_title", b_always=True)),
          ("Card ID", Field("@id")),
          ("Current phase", Field("@phase")),
          ("First revert", Field("first_revert_date", b_always=True)),
          ("Job go live", Field("job_go_live_date", b_always=True)),
          ("Material delivery", Field("material_delivery_date")),
          ("Brief owner", Field("brief_owner")),
     ],

     # ---------------------------------------------------------------- #
     # The linked-vs-standalone switch.
     #
     # is_this_job_part_of_an_approved_campaign == "Yes"
     #      -> the `campaign` connector points at a Campaign Planning DB
     #         record, and campaign context is INHERITED from it.
     # == "No"
     #      -> the form reveals originating_opco / strategic_pillar /
     #         target_audience / target_audience_additional_information /
     #         kpi_pillar on the brief itself. The brief IS the campaign.
     #
     # Both sets of ids are identical across the two boards, which is why one
     # resolver covers both cases instead of two layouts.
     # ---------------------------------------------------------------- #
     d_campaign={
          "s_field_id": "campaign",
          "s_label_hint": "Select campaign",
          "s_gate_field": "is_this_job_part_of_an_approved_campaign",
          "s_gate_value": "Yes",
          "s_table_id": CAMPAIGN_TABLE_ID,
          "s_section_title": "Campaign context",
          "s_note_linked": "Inherited from the approved campaign record. "
                           "Campaign Planning is the source of truth for these values.",
          "s_note_standalone": "This brief is not linked to an approved campaign — "
                               "it defines its own campaign context below.",
          "s_note_missing": "This brief is marked as part of an approved campaign, "
                            "but no campaign is linked. The context below is missing "
                            "and should be corrected in Pipefy before work starts.",
          # Printed off the LINKED RECORD. A curated subset — a brief should be
          # readable, not a reprint of the whole campaign record.
          "l_summary_fields": [
               Field("campaign_name"),
               Field("originating_opco"),
               Field("tier"),
               Field("campaign_go_live_date"),
               Field("campaign_end_date"),
               Field("product_go_live_date"),
               Field("campaign_budget"),
               Field("strategic_pillar"),
               Field("campaign_objective", s_render="block"),
               Field("campaign_background", s_render="block"),
               Field("key_message", s_render="block"),
               Field("what_problem_are_we_solving_for_the_customer", s_render="block"),
               Field("target_audience"),
               Field("target_audience_additional_information", s_render="block"),
               Field("kpi_pillar"),
               Field("kpi_additional_information", s_render="block"),
               Field("key_milestones", s_render="block"),
          ],
          # Printed off THE BRIEF when no campaign is linked. Exactly the five
          # fields the form reveals on "No", plus the strategic element.
          "l_standalone_fields": [
               Field("originating_opco", b_always=True),
               Field("strategic_pillar"),
               Field("target_audience"),
               Field("target_audience_additional_information", s_render="block"),
               Field("kpi_pillar"),
          ],
     },

     l_sections=[
          Section("Job information", [
               Field("job_name"),
               Field("brief_type", b_always=True),
               Field("tier", s_source="auto", b_always=True),
               Field("originating_opco", s_source="auto", b_always=True),
               OneOf("Division", L_DIVISION_FIELDS),
          ]),

          Section("Channels and elements", [
               Field("required_channels"),
               Field("atl_elements"),
               Field("btl_elements"),
               Field("digital_elements"),
               Field("internal_communications_elements"),
               Field("sponsorship_and_activation_elements"),
               Field("pr_elements"),
          ]),

          Section("Job timelines", [
               Field("first_revert_date", b_always=True),
               Field("job_go_live_date", b_always=True),
               Field("material_delivery_date"),
               Field("job_end_date"),
               Field("key_milestones", s_render="block"),
          ]),

          Section("Job details", [
               Field("the_brief_in_a_sentence"),
               Field("job_objective", s_render="block"),
               Field("job_background", s_render="block"),
               Field("key_message", s_render="block"),
               Field("key_requirements", s_render="block"),
               Field("strategic_pillar", s_source="auto"),
               Field("target_audience", s_source="auto"),
               Field("target_audience_other"),
               Field("target_audience_additional_information", s_source="auto",
                     s_render="block"),
          ]),

          Section("Budget", [
               Field("ugandan_promotion_budget"),
               Field("ugandan_positioning_budget"),
               Field("ugandan_proposition_budget"),
               Field("zambian_promotion_budget"),
               Field("zambian_positioning_budget"),
               Field("zambian_proposition_budget"),
          ]),

          Section("KPIs", [
               Field("kpi_pillar", s_source="auto"),
               Field("kpi_pillar_other_please_specify"),
               Field("awareness_kpi"),
               Field("awareness_kpi_other_please_specify"),
               Field("acquisition_growth_kpi"),
               Field("acquisition_growth_kpi_other_please_specify"),
               Field("digital_communication_kpi"),
               Field("digital_communication_kpi_other_please_specify"),
               Field("brand_desire_kpi"),
               Field("brand_desire_kpi_other_please_specify"),
               Field("nps_kpi"),
               Field("nps_kpi_other_please_specify"),
          ]),

          Section("Reference material", [
               Field("creative_inspiration"),
               Field("creative_inspiration_attachment_s"),
               Field("creative_inspiration_free_text_link_s", s_render="block"),
               Field("faqs_and_customer_journey"),
               Field("faqs_and_customer_journey_attachment_s"),
               Field("faqs_and_customer_journey_free_text_link_s", s_render="block"),
               Field("competitor_context"),
               Field("competitor_context_attachment_s"),
               Field("competitor_context_free_text_link_s", s_render="block"),
               Field("go_to_market_plan"),
               Field("go_to_market_plan_attachment_s"),
               Field("go_to_market_plan_free_text_link_s", s_render="block"),
               Field("existing_assets_for_reference_or_use"),
               Field("existing_assets_for_reference_or_use_attachment_s"),
               Field("existing_assets_for_reference_or_use_free_text_link_s",
                     s_render="block"),
          ]),
     ],

     l_tail_sections=[
          Section("Approvals", [
               Field("reviewer", s_label="Reviewer - 1st approval"),
               Field("job_review_decision", s_label="Decision - 1st approval"),
               Field("reviewer_1", s_label="Reviewer - 2nd approval"),
               Field("job_review_decision_1", s_label="Decision - 2nd approval"),
               Field("reviewer_2", s_label="Reviewer - 3rd approval"),
               Field("job_review_decision_2", s_label="Decision - 3rd approval"),
          ]),
     ],

     # ---------------------------------------------------------------- #
     # THIS FILE IS COPIED ONTO EVERY AGENCY CARD.
     #
     # The fan-out automations on Brief Submitted copy brief_attached from the
     # briefing card to each agency's Agency Workflow card. So the Job Brief is
     # read by external agencies, and the agency roster stays off it — Curiosity
     # does not need to know EXP is on the same job.
     #
     # review_feedback / feedback / feedback_1 are internal approval commentary
     # and are denied for the same reason. Move them into the Approvals section
     # above if MTN decides otherwise.
     # ---------------------------------------------------------------- #
     set_deny={
          "brief_attached",                             # circular
          "campaign",                                   # connector, holds a record id
          "is_this_job_part_of_an_approved_campaign",   # said better by the campaign section
          "zambia_agencies_required",                   # agency roster — see above
          "uganda_agencies_required",                   # agency roster — see above
          "review_feedback",                            # internal approval commentary
          "feedback",                                   # internal approval commentary
          "feedback_1",                                 # internal approval commentary
          "does_this_decision_need_a_second_approver",
          "does_this_decision_need_a_third_approver",
          "_",                                          # blank-label junk on Brief Updates
     },
)


'''
     *****************************************************
           REGISTRY
     *****************************************************
'''

L_PROFILES = [D_CAMPAIGN_BRIEF, D_JOB_BRIEF]
D_PROFILE_BY_KEY = {o_doc.s_key: o_doc for o_doc in L_PROFILES}
D_PROFILE_BY_PIPE = {o_doc.s_pipe_id: o_doc for o_doc in L_PROFILES}


def fn_profile_for_pipe(s_pipe_id=""):
     '''
          The Doc for a pipe id, or None. None is a 409 to the caller — the card
          is real but this integration has nothing to say about its pipe.
     '''
     try:
          return D_PROFILE_BY_PIPE.get(str(s_pipe_id))
     except Exception:
          return None


def fn_profile_for_key(s_key=""):
     '''
          The Doc for a profile key ("campaign" / "brief"), or None.
     '''
     try:
          return D_PROFILE_BY_KEY.get(str(s_key))
     except Exception:
          return None


def fn_allowed_field_ids(o_doc=None, s_scope="pipe") -> set:
     '''
          Every field id this document is allowed to print, for one scope.

          The two scopes live on different Pipefy objects and must never be
          compared against each other — that is what makes the drift check
          meaningful rather than noisy:

            "pipe"      ids on the document's own pipe form. Includes
                        l_standalone_fields, which are read off the brief when
                        no campaign is linked.
            "campaign"  ids on the linked Campaign Planning DB table
                        (l_summary_fields only).

          Used by check_drift.py.
     '''
     try:
          if s_scope == "campaign":
               l_loose = list(o_doc.d_campaign.get("l_summary_fields") or [])
          else:
               l_loose = list(o_doc.l_subtitle)
               l_loose += [t_pair[1] for t_pair in o_doc.l_meta]
               if o_doc.t_highlight:
                    l_loose.append(o_doc.t_highlight[1])
               l_loose += list(o_doc.d_campaign.get("l_standalone_fields") or [])
               for o_section in list(o_doc.l_sections) + list(o_doc.l_tail_sections):
                    l_loose += list(o_section.l_items)
               s_gate = o_doc.d_campaign.get("s_gate_field") or ""
               if s_gate:
                    l_loose.append(Field(s_gate))

          set_ids = set()
          for o_item in l_loose:
               if isinstance(o_item, OneOf):
                    set_ids.update(o_item.l_field_ids)
               elif not o_item.s_field_id.startswith("@"):
                    set_ids.add(o_item.s_field_id)
          return set_ids
     except Exception:
          return set()

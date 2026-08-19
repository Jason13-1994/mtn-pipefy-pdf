---
title: Field inventory — all three pipes + Campaign Planning DB
generated: by tools/recon_pdf_boards.py from the 2026-08-05 API capture
note: regenerate before build. Do not hand-edit.
---

# 01a — Field inventory

`JUNK` = blank-label or placeholder field that must never reach a client-facing PDF.
`OPTS` = option count for select/checklist fields.

## Campaign Planning — `307284211`

61 start-form fields.

### Start form

| Section | Field id | Label | Type | Req | Opts |
|---|---|---|---|---|---|
| _(pre-section)_ | `campaign_attached` | Campaign attached | attachment |  |  |
| _(pre-section)_ | `approver_email` | Approver email | email |  |  |
| _(pre-section)_ | `campaign_owner` | Campaign owner | assignee_select |  |  |
| Campaign Information | `campaign_name` | Campaign name | short_text | Y |  |
| Campaign Information | `originating_opco` | Originating OpCo | select | Y | 2 |
| Campaign Information | `uganda_division` | Uganda division | select | Y | 16 |
| Campaign Information | `uganda_marketing_division` | Uganda marketing division | select | Y | 5 |
| Campaign Information | `uganda_finance_division` | Uganda finance division | select | Y | 3 |
| Campaign Information | `uganda_enterprise_division` | Uganda enterprise division | select | Y | 3 |
| Campaign Information | `uganda_technology_division` | Uganda technology division | select | Y | 3 |
| Campaign Information | `uganda_corporate_services_division` | Uganda corporate services division | select | Y | 2 |
| Campaign Information | `uganda_business_intelligence_division` | Uganda business intelligence division | select | Y | 1 |
| Campaign Information | `zambia_division` | Zambia division | select | Y | 12 |
| Campaign Information | `zambia_marketing_division` | Zambia marketing division | select | Y | 7 |
| Campaign Information | `zambia_enterprise_business_unit_ebu` | Zambia enterprise business unit (EBU) | select | Y | 3 |
| Campaign Information | `zambia_mtn_home_division` | Zambia MTN home division | select | Y | 2 |
| Campaign Information | `zambia_finance_division` | Zambia finance division | select | Y | 5 |
| Campaign Information | `zambia_technology_division` | Zambia technology division | select | Y | 2 |
| Campaign Information | `zambia_corporate_services` | Zambia corporate services | select | Y | 2 |
| Campaign Information | `tier` | Tier | select | Y | 3 |
| Campaign Timelines | `campaign_year` | Campaign year | number | Y |  |
| Campaign Timelines | `campaign_go_live_date` | Campaign go live date | date | Y |  |
| Campaign Timelines | `campaign_end_date` | Campaign end date | date | Y |  |
| Campaign Timelines | `product_go_live_date` | Product go live date | date |  |  |
| Campaign Timelines | `key_milestones` | Key milestones | long_text |  |  |
| Campaign Details | `campaign_budget` | Campaign budget | currency |  |  |
| Campaign Details | `strategic_pillar` | Strategic element | checklist_vertical | Y | 3 |
| Campaign Details | `zambian_promotion_budget` | Zambian promotion budget | currency |  |  |
| Campaign Details | `copy_of_zambian_promotion_budget` | Ugandan promotion budget | currency |  |  |
| Campaign Details | `zambian_positioning_budget` | Zambian positioning budget | currency |  |  |
| Campaign Details | `ugandan_positioning_budget` | Ugandan positioning budget | currency |  |  |
| Campaign Details | `zambian_proposition_budget` | Zambian proposition budget | currency |  |  |
| Campaign Details | `ugandan_proposition_budget` | Ugandan proposition budget | currency |  |  |
| Campaign Details | `campaign_objective` | Campaign objective | long_text | Y |  |
| Campaign Details | `campaign_background` | Campaign background | long_text | Y |  |
| Campaign Details | `key_message` | Key message | long_text | Y |  |
| Campaign Details | `what_problem_are_we_solving_for_the_customer` | What problem are we solving for the customer | long_text | Y |  |
| Campaign Details | `target_audience` | Target audience | checklist_vertical | Y | 11 |
| Campaign Details | `target_audience_other` | Target audience - other | short_text | Y |  |
| Campaign Details | `target_audience_additional_information` | Target audience additional information | long_text |  |  |
| Campaign KPI's | `kpi_pillar` | KPI pillar | checklist_vertical | Y | 7 |
| Campaign KPI's | `kpi_pillar_other` | KPI pillar other | short_text | Y |  |
| Campaign KPI's | `awareness_kpi` | Awareness KPI | checklist_vertical |  | 7 |
| Campaign KPI's | `awareness_kpi_other` | Awareness KPI - other | short_text | Y |  |
| Campaign KPI's | `acquisition_growth_kpi` | Acquisition & growth KPI | checklist_vertical |  | 8 |
| Campaign KPI's | `acquisition_and_growth_kpi_other` | Acquisition and growth KPI - other | short_text | Y |  |
| Campaign KPI's | `digital_communication_kpi` | Digital communication KPI | checklist_vertical |  | 14 |
| Campaign KPI's | `digital_communication_kpi_other` | Digital communication KPI - other | short_text | Y |  |
| Campaign KPI's | `brand_desire_kpi` | Brand desire KPI | checklist_vertical |  | 2 |
| Campaign KPI's | `brand_desire_kpi_other` | Brand desire KPI - other | short_text | Y |  |
| Campaign KPI's | `nps_kpi` | NPS KPI | checklist_vertical |  | 4 |
| Campaign KPI's | `nps_kpi_other` | NPS KPI other | short_text | Y |  |
| Campaign KPI's | `kpi_additional_information` | KPI additional information | long_text |  |  |
| Supporting Information | `supporting_documentation` | Supporting documentation | checklist_horizontal |  | 2 |
| Supporting Information | `supporting_documents_attachment_s` | Supporting documents attachment(s) | attachment |  |  |
| Supporting Information | `supporting_documents_free_text_link_s` | Supporting documents free text / link(s) | long_text |  |  |

### Phase fields

| Phase | Field id | Label | Type |
|---|---|---|---|
| Campaign Review | `reviewer` | Reviewer | assignee_select |
| Campaign Review | `campaign_review_decision` | Campaign review decision | radio_horizontal |
| Campaign Review | `reviewer_comments` | Reviewer comments | long_text |
| Approved Campaigns | `campaign_approval_date` | Campaign Approval Date | date |
| Approved Campaigns | `approval_authority` | Approval Authority | select |
| Approved Campaigns | `approval_notes` | Approval Notes | long_text |
| Approved Campaigns | `approval_document` | Approval Document | attachment |
| Approved Campaigns | `approval_status` | Approval Status | radio_horizontal |
| Cancelled Campaigns | `reason_for_cancellation` | Reason for Cancellation | radio_vertical |
| Cancelled Campaigns | `cancellation_date` | Cancellation Date | date |
| Cancelled Campaigns | `lessons_learned` | Lessons Learned | long_text |
| Cancelled Campaigns | `stakeholder_feedback` | Stakeholder Feedback | long_text |
| Cancelled Campaigns | `next_steps_post_cancellation` | Next Steps Post-Cancellation | checklist_vertical |

## Campaign Briefing — `307284210`

82 start-form fields.

### Start form

| Section | Field id | Label | Type | Req | Opts |
|---|---|---|---|---|---|
| _(pre-section)_ | `brief_attached` | Brief attached | attachment |  |  |
| _(pre-section)_ | `brief_owner` | Brief owner | assignee_select |  |  |
| Job information | `is_this_job_part_of_an_approved_campaign` | Is this job part of an approved campaign? | radio_horizontal | Y | 2 |
| Job information | `campaign` | Select campaign | connector | Y |  |
| Job information | `job_name` | Job name | short_text | Y |  |
| Job information | `brief_type` | Brief type | select | Y | 5 |
| Job information | `tier` | Tier | select | Y | 3 |
| Job information | `originating_opco` | Originating OpCo | select | Y | 2 |
| Job information | `uganda_division` | Uganda division | select | Y | 15 |
| Job information | `uganda_marketing_division` | Uganda marketing division | select |  | 5 |
| Job information | `uganda_finance_division` | Uganda finance division | select | Y | 3 |
| Job information | `uganda_enterprise_division` | Uganda enterprise division | select | Y | 3 |
| Job information | `uganda_technology_division` | Uganda technology division | select | Y | 3 |
| Job information | `uganda_corporate_services_division` | Uganda corporate services division | select | Y | 2 |
| Job information | `uganda_business_intelligence_division` | Uganda business intelligence division | select | Y | 1 |
| Job information | `zambia_division` | Zambia division | select | Y | 12 |
| Job information | `zambia_marketing_division` | Zambia marketing division | select | Y | 7 |
| Job information | `zambia_enterprise_business_unit_ebu` | Zambia enterprise business unit (EBU) | select | Y | 3 |
| Job information | `zambia_mtn_home_division` | Zambia MTN home division | select | Y | 2 |
| Job information | `zambia_finance_division` | Zambia finance division | select | Y | 5 |
| Job information | `zambia_technology_division` | Zambia technology division | select | Y | 2 |
| Job information | `zambia_corporate_services` | Zambia corporate services | select | Y | 2 |
| Channels and elements | `required_channels` | Required channels | checklist_vertical | Y | 7 |
| Channels and elements | `atl_elements` | ATL elements | checklist_vertical |  | 8 |
| Channels and elements | `btl_elements` | BTL elements | checklist_vertical |  | 10 |
| Channels and elements | `digital_elements` | Digital elements | checklist_vertical |  | 22 |
| Channels and elements | `internal_communications_elements` | Internal communications elements | checklist_vertical |  | 12 |
| Channels and elements | `sponsorship_and_activation_elements` | Sponsorship and activation elements | checklist_vertical |  | 16 |
| Channels and elements | `pr_elements` | PR elements | checklist_vertical |  | 50 |
| Job timelines | `first_revert_date` | First revert date | datetime | Y |  |
| Job timelines | `job_go_live_date` | Job go live date | date | Y |  |
| Job timelines | `material_delivery_date` | Material delivery date | date |  |  |
| Job timelines | `job_end_date` | Job end date | date | Y |  |
| Job timelines | `key_milestones` | Key milestones | long_text |  |  |
| Job details | `the_brief_in_a_sentence` | The brief in a sentence | short_text | Y |  |
| Job details | `job_objective` | Job objective | long_text | Y |  |
| Job details | `job_background` | Job background | long_text | Y |  |
| Job details | `key_message` | Key message | long_text | Y |  |
| Job details | `key_requirements` | Key requirements | long_text | Y |  |
| Job details | `creative_inspiration` | Creative inspiration | checklist_horizontal |  | 2 |
| Job details | `creative_inspiration_attachment_s` | Creative inspiration attachment(s) | attachment | Y |  |
| Job details | `creative_inspiration_free_text_link_s` | Creative inspiration free text / link(s) | long_text | Y |  |
| Job details | `faqs_and_customer_journey` | FAQs and customer journey | checklist_horizontal |  | 2 |
| Job details | `faqs_and_customer_journey_attachment_s` | FAQs and customer journey attachment(s) | attachment | Y |  |
| Job details | `faqs_and_customer_journey_free_text_link_s` | FAQs and customer journey free text / link(s) | long_text | Y |  |
| Job details | `strategic_pillar` | Strategic element | select | Y | 3 |
| Job details | `ugandan_promotion_budget` | Ugandan promotion budget | currency |  |  |
| Job details | `zambian_promotion_budget` | Zambian promotion budget | currency |  |  |
| Job details | `ugandan_positioning_budget` | Ugandan positioning budget | currency |  |  |
| Job details | `zambian_positioning_budget` | Zambian positioning budget | currency |  |  |
| Job details | `ugandan_proposition_budget` | Ugandan proposition budget | currency |  |  |
| Job details | `zambian_proposition_budget` | Zambian proposition budget | currency |  |  |
| Job details | `target_audience` | Target audience | checklist_vertical | Y | 11 |
| Job details | `target_audience_other` | Target audience - other | short_text | Y |  |
| Job details | `target_audience_additional_information` | Target audience additional information | long_text |  |  |
| Job details | `competitor_context` | Competitor context | checklist_horizontal |  | 2 |
| Job details | `competitor_context_attachment_s` | Competitor context attachment(s) | attachment | Y |  |
| Job details | `competitor_context_free_text_link_s` | Competitor context free text / link(s) | long_text | Y |  |
| Job details | `go_to_market_plan` | Go to market plan | checklist_horizontal |  | 2 |
| Job details | `go_to_market_plan_attachment_s` | Go to market plan attachment(s) | attachment | Y |  |
| Job details | `go_to_market_plan_free_text_link_s` | Go to market plan free text / link(s) | long_text | Y |  |
| Job details | `kpi_pillar` | KPI pillar | checklist_vertical | Y | 7 |
| Job details | `kpi_pillar_other_please_specify` | KPI pillar - other | short_text | Y |  |
| Job details | `awareness_kpi` | Awareness KPI | checklist_vertical |  | 7 |
| Job details | `awareness_kpi_other_please_specify` | Awareness KPI - other | short_text | Y |  |
| Job details | `acquisition_growth_kpi` | Acquisition & growth KPI | checklist_vertical |  | 8 |
| Job details | `acquisition_growth_kpi_other_please_specify` | Acquisition & growth KPI - other | short_text | Y |  |
| Job details | `digital_communication_kpi` | Digital communication KPI | checklist_vertical |  | 14 |
| Job details | `digital_communication_kpi_other_please_specify` | Digital communication KPI - other | short_text | Y |  |
| Job details | `brand_desire_kpi` | Brand desire KPI | checklist_vertical |  | 6 |
| Job details | `brand_desire_kpi_other_please_specify` | Brand desire KPI - other | short_text | Y |  |
| Job details | `nps_kpi` | NPS KPI | checklist_vertical |  | 4 |
| Job details | `nps_kpi_other_please_specify` | NPS KPI - other | short_text | Y |  |
| Job details | `zambia_agencies_required` | Zambia agencies required | checklist_vertical | Y | 3 |
| Job details | `uganda_agencies_required` | Uganda agencies required | checklist_vertical | Y | 13 |
| Job details | `existing_assets_for_reference_or_use` | Existing assets for reference or use | checklist_horizontal |  | 2 |
| Job details | `existing_assets_for_reference_or_use_attachment_s` | Existing assets for reference or use attachment(s) | attachment | Y |  |
| Job details | `existing_assets_for_reference_or_use_free_text_link_s` | Existing assets for reference or use free text / link(s) | long_text | Y |  |

### Phase fields

| Phase | Field id | Label | Type |
|---|---|---|---|
| Brief Review - 1st Approval | `reviewer` | Reviewer | assignee_select |
| Brief Review - 1st Approval | `job_review_decision` | Job review decision | radio_horizontal |
| Brief Review - 1st Approval | `does_this_decision_need_a_second_approver` | Does this decision need a second approver? | radio_horizontal |
| Brief Review - 1st Approval | `review_feedback` | Review Feedback | long_text |
| Brief Review - 2nd Approval | `reviewer_1` | Reviewer | assignee_select |
| Brief Review - 2nd Approval | `job_review_decision_1` | Job review decision | radio_horizontal |
| Brief Review - 2nd Approval | `does_this_decision_need_a_third_approver` | Does this decision need a third approver? | radio_horizontal |
| Brief Review - 2nd Approval | `feedback` | Feedback | long_text |
| Brief Review - 3rd Approval | `reviewer_2` | Reviewer | assignee_select |
| Brief Review - 3rd Approval | `job_review_decision_2` | Job review decision | radio_horizontal |
| Brief Review - 3rd Approval | `feedback_1` | Feedback | long_text |
| Brief Updates | `_` | _ | checklist_vertical |

## Agency Workflow — `307284207`

88 start-form fields.

### Start form

| Section | Field id | Label | Type | Req | Opts |
|---|---|---|---|---|---|
| _(pre-section)_ | `cost_timing_plan` | Cost & timing plan | attachment |  |  |
| _(pre-section)_ | `brief_attached` | Brief attached | attachment |  |  |
| _(pre-section)_ | `card_title` | Card title | short_text |  |  |
| _(pre-section)_ | `creative_team` | Team | select |  | 16 |
| _(pre-section)_ | `reviewer` | Reviewer | assignee_select |  |  |
| _(pre-section)_ | `brief_owner` | Brief owner | assignee_select |  |  |
| _(pre-section)_ | `button` | Button **JUNK** | long_text |  |  |
| Job information | `is_this_job_part_of_an_approved_campaign` | Is this job part of an approved campaign? | radio_horizontal |  | 2 |
| Job information | `select_campaign` | Select campaign | connector |  |  |
| Job information | `job_name` | Job name | short_text |  |  |
| Job information | `brief_type` | Brief type | select |  | 5 |
| Job information | `tier` | Tier | select |  | 3 |
| Job information | `originating_opco` | Originating OpCo | select |  | 2 |
| Job information | `uganda_division` | Uganda division | select |  | 16 |
| Job information | `uganda_marketing_division` | Uganda marketing division | select |  | 4 |
| Job information | `uganda_finance_division` | Uganda finance division | select |  | 3 |
| Job information | `uganda_enterprise_division` | Uganda enterprise division | select |  | 3 |
| Job information | `uganda_technology_division` | Uganda technology division | select |  | 2 |
| Job information | `uganda_corporate_services_division_1` | Uganda corporate services division | select |  | 2 |
| Job information | `uganda_business_intelligence_division` | Uganda business intelligence division | select |  | 1 |
| Job information | `zambia_division` | Zambia division | select |  | 18 |
| Job information | `zambia_enterprise_business_unit_ebu` | Zambia enterprise business unit (EBU) | select |  | 3 |
| Job information | `zambia_marketing_division` | Zambia marketing division | select |  | 7 |
| Job information | `zambia_mtn_home_division` | Zambia MTN home division | select |  | 2 |
| Job information | `zambia_finance_division` | Zambia finance division | select |  | 5 |
| Job information | `zambia_technology_division` | Zambia technology division | select |  | 2 |
| Job information | `zambia_corporate_services` | Zambia corporate services | select |  | 2 |
| Channels and elements | `required_channels` | Required channels | checklist_vertical |  | 6 |
| Channels and elements | `atl_elements` | ATL elements | checklist_vertical |  | 7 |
| Channels and elements | `btl_elements` | BTL elements | checklist_vertical |  | 10 |
| Channels and elements | `digital_elements` | Digital elements | checklist_vertical |  | 22 |
| Channels and elements | `internal_communications_elements` | Internal communications elements | checklist_vertical |  | 12 |
| Channels and elements | `sponsorship_and_activation_elements` | Sponsorship and activation elements | checklist_vertical |  | 16 |
| Channels and elements | `pr_elements` | PR elements | checklist_vertical |  | 50 |
| Job timelines | `first_revert_date` | First revert date | datetime |  |  |
| Job timelines | `job_go_live_date` | Job go live date | date |  |  |
| Job timelines | `material_delivery_date` | Material delivery date | date |  |  |
| Job timelines | `job_end_date` | Job end date | date |  |  |
| Job timelines | `key_milestones` | Key milestones | long_text |  |  |
| Job details | `the_brief_in_a_sentence` | The brief in a sentence | short_text |  |  |
| Job details | `job_objective` | Job objective | long_text |  |  |
| Job details | `job_background` | Job background | long_text |  |  |
| Job details | `key_message` | Key message | long_text |  |  |
| Job details | `key_requirements` | Key requirements | long_text |  |  |
| Job details | `creative_inspiration` | Creative inspiration | checklist_horizontal |  | 2 |
| Job details | `creative_inspiration_attachment_s` | Creative inspiration attachment(s) | attachment |  |  |
| Job details | `creative_inspiration_free_text_link_s` | Creative inspiration free text / link(s) | long_text |  |  |
| Job details | `faqs_and_customer_journey` | FAQs and customer journey | checklist_horizontal |  | 2 |
| Job details | `faqs_and_customer_journey_attachment_s` | FAQs and customer journey attachment(s) | attachment |  |  |
| Job details | `faqs_and_customer_journey_free_text_link_s` | FAQs and customer journey free text / link(s) | long_text |  |  |
| Job details | `target_audience` | Target audience | checklist_vertical |  | 11 |
| Job details | `target_audience_other` | Target audience - other | short_text |  |  |
| Job details | `strategic_element` | Strategic element | select |  | 3 |
| Job details | `ugandan_promotion_budget` | Ugandan promotion budget | currency |  |  |
| Job details | `zambian_positioning_budget` | Zambian positioning budget | currency |  |  |
| Job details | `ugandan_positioning_budget` | Ugandan positioning budget | currency |  |  |
| Job details | `zambian_promotion_budget` | Zambian promotion budget | currency |  |  |
| Job details | `ugandan_proposition_budget` | Ugandan proposition budget | currency |  |  |
| Job details | `zambian_proposition_budget` | Zambian proposition budget | currency |  |  |
| Job details | `competitor_context` | Competitor context | checklist_horizontal |  | 2 |
| Job details | `target_audience_additional_information` | Target audience additional information | long_text |  |  |
| Job details | `competitor_context_attachment_s` | Competitor context attachment(s) | attachment |  |  |
| Job details | `competitor_context_free_text_link_s` | Competitor context free text / link(s) | long_text |  |  |
| Job details | `go_to_market_plan` | Go to market plan | checklist_horizontal |  | 2 |
| Job details | `go_to_market_plan_attachment_s` | Go to market plan attachment(s) | attachment |  |  |
| Job details | `go_to_market_plan_free_text_link_s` | Go to market plan free text / link(s) | long_text |  |  |
| Job details | `kpi_pillar` | KPI pillar | checklist_vertical |  | 5 |
| Job details | `kpi_pillar_other` | KPI pillar other | short_text |  |  |
| Job details | `awareness_kpi` | Awareness KPI | checklist_vertical |  | 6 |
| Job details | `awareness_kpi_other` | Awareness KPI - other | short_text |  |  |
| Job details | `acquisition_growth_kpi` | Acquisition & growth KPI | checklist_vertical |  | 7 |
| Job details | `acquisition_growth_kpi_other` | Acquisition & growth KPI - other | short_text |  |  |
| Job details | `digital_communication_kpi_other` | Digital communication KPI - other | short_text |  |  |
| Job details | `digital_communication_kpi` | Digital communication KPI | checklist_vertical |  | 13 |
| Job details | `brand_desire_kpi` | Brand desire KPI | checklist_vertical |  | 4 |
| Job details | `nps_kpi` | NPS KPI | checklist_vertical |  | 3 |
| Deliverables | `existing_assets_for_reference_or_use` | Existing assets for reference or use | checklist_horizontal |  | 2 |
| Deliverables | `brand_desire_kpi_other` | Brand desire KPI - other | short_text |  |  |
| Deliverables | `existing_assets_for_reference_or_use_attachment_s` | Existing assets for reference or use attachment(s) | attachment |  |  |
| Deliverables | `existing_assets_for_reference_or_use_free_text_link_s` | Existing assets for reference or use free text / link(s) | long_text |  |  |
| Deliverables | `nps_kpi_other` | NPS KPI - other | short_text |  |  |
| Deliverables | `zambia_agencies_required` | Zambia agencies required | checklist_vertical |  | 3 |
| Deliverables | `uganda_agencies_required` | Uganda agencies required | checklist_vertical |  | 13 |

### Phase fields

| Phase | Field id | Label | Type |
|---|---|---|---|
| Backlog | `_` | _ | checklist_vertical |
| Backlog | `studio_team` | Studio team | assignee_select |
| Cost & Timing | `zambian_promotion_budget_cost_timing` | Zambian promotion budget (Cost & Timing) | currency |
| Cost & Timing | `ugandan_promotion_budget_cost_timing` | Ugandan promotion budget (Cost & Timing) | currency |
| Cost & Timing | `zambian_positioning_budget_cost_timing` | Zambian positioning budget (Cost & Timing) | currency |
| Cost & Timing | `ugandan_positioning_budget_cost_timing` | Ugandan positioning budget (Cost & Timing) | currency |
| Cost & Timing | `zambian_proposition_budget_cost_timing` | Zambian proposition budget (Cost & Timing) | currency |
| Cost & Timing | `ugandan_proposition_budget_cost_timing` | Ugandan proposition budget (Cost & Timing) | currency |
| Cost & Timing - 1st Approval | `reviewer_1st_approval` | Reviewer - 1st Approval | assignee_select |
| Cost & Timing - 1st Approval | `cost_and_timing_1st_review` | Cost and timing - 1st review | radio_horizontal |
| Cost & Timing - 1st Approval | `does_this_decision_need_a_second_approval` | Does this decision need a second approval? | radio_horizontal |
| Cost & Timing - 1st Approval | `feedback` | Feedback | long_text |
| Cost & Timing - 2nd Approval | `reviewer_2` | Reviewer | assignee_select |
| Cost & Timing - 2nd Approval | `cost_and_timing_2nd_review` | Cost and timing - 2nd review | radio_horizontal |
| Cost & Timing - 2nd Approval | `feedback_1` | Feedback | long_text |
| Work In Progress | `__1` | _ | checklist_vertical |
| Recon & Billing | `finance_recon_and_billing` | Finance Recon and Billing | checklist_vertical |

## Campaign Planning DB — `mOUzRnnK` (URL id 307284208)

60 fields.

| Field id | Label | Type |
|---|---|---|
| `campaign_owner` | Campaign owner | assignee_select |
| `field` | **JUNK (blank label)** | checklist_vertical |
| `campaign_name` | Campaign name | short_text |
| `originating_opco` | Originating OpCo | select |
| `segment_business_unit` | Segment/business unit | select |
| `uganda_division` | Uganda division | select |
| `uganda_marketing_division` | Uganda marketing division | select |
| `uganda_finance_division` | Uganda finance division | select |
| `uganda_enterprise_division` | Uganda enterprise division | select |
| `uganda_technology_division` | Uganda technology division | select |
| `uganda_corporate_services_division` | Uganda Corporate services division | select |
| `uganda_business_intelligence_division` | Uganda business intelligence division | select |
| `uganda_products` | Uganda products | select |
| `zambia_division` | Zambia division | select |
| `zambia_products` | Zambia products | checklist_vertical |
| `tier` | Tier | select |
| `field_1` | **JUNK (blank label)** | checklist_vertical |
| `campaign_go_live_date` | Campaign go live date | date |
| `campaign_end_date` | Campaign end date | date |
| `product_go_live_date` | Product go live date | date |
| `key_milestones` | Key Milestones | long_text |
| `field_2` | **JUNK (blank label)** | checklist_vertical |
| `campaign_budget` | Campaign budget | currency |
| `strategic_pillar` | Strategic pillar | checklist_vertical |
| `campaign_objective` | Campaign objective | long_text |
| `campaign_background` | Campaign background | long_text |
| `key_message` | Key message | long_text |
| `what_problem_are_we_solving_for_the_customer` | What problem are we solving for the customer | long_text |
| `target_audience` | Target audience | checklist_vertical |
| `target_audience_core` | Target audience core | checklist_vertical |
| `target_audience_internal` | Target audience internal | checklist_vertical |
| `target_audience_other` | Target audience - other | checklist_vertical |
| `new_target_audience` | New target audience | long_text |
| `target_audience_additional_information` | Target audience additional information | long_text |
| `field_3` | **JUNK (blank label)** | checklist_vertical |
| `kpi_pillar` | KPI pillar | checklist_vertical |
| `awareness_kpi` | Awareness KPI | checklist_vertical |
| `acquisition_growth_kpi` | Acquisition & Growth KPI | checklist_vertical |
| `digital_communication_kpi` | Digital Communication KPI | checklist_vertical |
| `brand_desire_kpi` | Brand Desire KPI | checklist_vertical |
| `nps_kpi` | NPS KPI | checklist_vertical |
| `kpi_additional_information` | KPI additional information | long_text |
| `field_4` | **JUNK (blank label)** | checklist_vertical |
| `supporting_documentation` | Supporting documentation | checklist_horizontal |
| `supporting_documents_attachment_s` | Supporting documents attachment(s) | attachment |
| `supporting_documents_free_text_link_s` | Supporting documents free text / link(s) | long_text |
| `campaign_attached` | Campaign attached | attachment |
| `approver_email` | Approver email | email |
| `zambia_marketing_division` | Zambia marketing division | select |
| `zambia_enterprise_business_unit_ebu` | Zambia enterprise business unit (EBU) | select |
| `zambia_mtn_home_division` | Zambia MTN home division | select |
| `zambia_finance_division` | Zambia finance division | select |
| `zambia_technology_division` | Zambia technology division | select |
| `zambia_corporate_services` | Zambia corporate services | select |
| `kpi_pillar_other` | KPI pillar other | short_text |
| `awareness_kpi_other` | Awareness KPI - other | short_text |
| `acquisition_and_growth_kpi_other` | Acquisition and growth KPI - other | short_text |
| `digital_communication_kpi_other` | Digital communication KPI - other | short_text |
| `brand_desire_kpi_other` | Brand desire KPI - other | short_text |
| `nps_kpi_other` | NPS KPI other | short_text |

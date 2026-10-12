# Video scripts

Produced 2026-10-12. All videos render locally in Hyperframes 0.8.150. Captions are burned in; no voice or AI-generated imagery. The measured decision is to withhold gemini-3.8-flash, reject gemini-3.1-flash-lite, and keep classifier_v1 authoritative.

## Editorial and evidence rules

The owner requested a four-minute cut focused on all major screens and functionality. This replaces the original 7–8 minute target. The active edit covers Portfolio, Pipeline, Flow, Applications, Reviews, Business Case, Experiments, Decision Policy, Shadow, Release, Monitoring, Incidents, Audit, and Settings. Architecture and the recommendation close the tour.

Real console shots retain LIVE or DEMO and the DATA MODE banner. Existing demo bars were pinned for scrolling captures using capture-only inline styles; product source and backend were unchanged. Incidental numeric UI text, relative ages, axis ticks, compact money values, and list sequence markers were masked to respect the prompt’s approved-number list. Approved figures are supplied in the labelled captions below. The masks do not replace data with invented values. Model/config identifiers and diagram indices are identifiers, not metric claims.

No owner MOV, low-resolution walkthrough, OAuth, browser chrome, owner email, or customer case text appears in a final video. Reviews shows gate approvals only; the routed-case section is hidden during capture. Audit uses the local DEMO identities. Its final shot holds the real top capture; later event rows containing unapproved numeric prose are masked. In Reviews, the generated business problem’s unapproved written-out page count is also masked. The owner MOV was inventoried and sampled privately during the first run but not used. A first capture attempt scrolled to a hidden SVG icon; the final capture script uses real scrolling and succeeds on every requested route.

The experiment report spells the frozen count `1540`; its recorded release rationale spells the same frozen set `1,540`. For the required comma-formatted caption, the exact textual evidence is docs/release_recommendation.md, with docs/experiment_report.md as the primary experiment evidence. Neither file was edited. The comparison uses the experiment report’s named configuration columns; no new model run was performed.

The repository cards intentionally say `REPO_URL` and “Placeholder — owner to insert repository link.” They are not live links.

## Teaser

| Time | Every caption / title-card text | Provenance | Shot / source | Evidence |
|---|---|---|---|---|
| 00:00–00:03 | Neither LLM shipped. | MEASURED | media/live/triage-release-dark.png; numeric overlay | `docs/release_recommendation.md` |
| 00:03–00:07 | 5 of 10 release gates passed. Activation withheld. | MEASURED | media/live/triage-release-dark.png; numeric overlay | `docs/release_recommendation.md` |
| 00:07–00:11 | Policy blocks moves without evidence. | SYNTHETIC | media/work/captures-final/pipeline-blocked.png; real blocked drag | `frontend/src/pages/Pipeline.tsx` |
| 00:11–00:16 | Drift detected. Automation paused.<br>Human review restored. | FIXTURE; MEASURED detection | media/live/triage-monitoring-dark.png; numeric overlay | `docs/incident_report.md` |
| 00:16–00:20.650 | Enterprise AI Control Plane<br>Governance that decides when not to ship. | — | Typographic title; console palette and Inter | No numeric claim |
| 00:20.650–00:21 | Neither LLM shipped. | MEASURED | Return transition to the opening real Release shot; no separate reading hold | `docs/release_recommendation.md` |

## Architecture overview

| Time | Every caption / title-card text | Provenance | Shot / source | Evidence |
|---|---|---|---|---|
| 00:00–00:05 | Enterprise AI Control Plane<br>Governance that decides when not to ship an AI model | — | Typographic card; console tokens and local Inter | No numeric claim |
| 00:05–00:10 | IAP protects the Cloud Run console. | — | docs/diagrams/01_system_overview.png; reveal rectangles over the unchanged PNG | No numeric claim |
| 00:10–00:15 | Cloud Run jobs produce evidence; Vertex AI supplies candidates. | — | docs/diagrams/01_system_overview.png; reveal rectangles over the unchanged PNG | No numeric claim |
| 00:15–00:20 | Firestore keeps records. BigQuery supports analysis. Cloud Storage keeps artifacts. | — | docs/diagrams/01_system_overview.png; reveal rectangles over the unchanged PNG | No numeric claim |
| 00:20–00:24 | Tune on development data. Freeze the policy. | MEASURED | docs/diagrams/06_experiment_to_release.png; moving outline over the unchanged PNG | `docs/release_recommendation.md` |
| 00:24–00:28 | 1,540 frozen cases. Scorecard, then gates. | MEASURED | docs/diagrams/06_experiment_to_release.png; moving outline over the unchanged PNG | `docs/experiment_report.md`, `docs/release_recommendation.md` |
| 00:28–00:31 | gemini-3.8-flash: 5 of 10 release gates. | MEASURED | docs/diagrams/06_experiment_to_release.png; moving outline over the unchanged PNG | `docs/release_recommendation.md` |
| 00:31–00:35 | Shadow replay. Decision: withhold. | SIMULATED; MEASURED | docs/diagrams/06_experiment_to_release.png; moving outline over the unchanged PNG | `docs/release_recommendation.md` |
| 00:35–00:40 | The registry enforces lifecycle moves. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 1 s after startup trim | No numeric claim |
| 00:40–00:45 | Release gates block activation. | MEASURED | media/live/triage-release-dark.png (numeric redaction overlay) | `docs/release_recommendation.md` |
| 00:45–00:50 | Pause automation. Restore human review. | FIXTURE; MEASURED | media/live/incidents-dark.png (numeric redaction overlay) | `docs/incident_report.md` |
| 00:50–00:56 | Withheld<br>Withheld: gemini-3.8-flash passed 5 of 10 release gates<br>on 1,540 frozen cases. | MEASURED | Typographic card; console tokens and local Inter | `docs/release_recommendation.md` |
| 00:56–00:58 | REPO_URL<br>Placeholder — owner to insert repository link | — | Typographic card; console tokens and local Inter | No numeric claim |

## Four-minute demo

| Time | Every caption / title-card text | Provenance | Shot / source | Evidence |
|---|---|---|---|---|
| 00:00–00:06 | Enterprise AI Control Plane<br>Decide what ships. Enforce the decision. | — | Typographic card; console tokens and local Inter | No numeric claim |
| 00:06–00:18 | Portfolio: investment, risk, spend, and bottlenecks<br>across a generated sample organization. | SYNTHETIC | media/work/captures-extra/portfolio.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 00:18–00:26 | Pipeline: drag Mortgage Document Q&A into Evaluation.<br>Its approvals are in place. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 00:26–00:35 | Meeting Notes is blocked: the business case is missing. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 8 s after startup trim | No numeric claim |
| 00:35–00:41 | Executive viewer: write controls disappear. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 17 s after startup trim | No numeric claim |
| 00:41–00:51 | Flow: see lifecycle movement and where apps stall. | SYNTHETIC | media/work/captures-final/flow.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 00:51–01:03 | Applications: search the registry by name, owner, or problem.<br>Filter by stage and health. | SYNTHETIC | media/work/captures-extra/applications.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 01:03–01:18 | Reviews: an independent reviewer checks evidence<br>and approves a gate. Submitters cannot approve themselves. | SYNTHETIC | media/work/captures-review-success/reviews.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 01:18–01:27 | Business Case: compare breakeven precision.<br>Classifier 0.849; high capability 0.865; low cost 0.864. | ASSUMPTION | media/work/captures-final/business.webm → processed local capture; source offset 0 s after startup trim | `docs/business_case.md` |
| 01:27–01:36 | Net monthly value: classifier $57,270;<br>high capability $66,957; low cost $62,130. | ASSUMPTION | media/work/captures-final/business.webm → processed local capture; source offset 9 s after startup trim | `docs/business_case.md` |
| 01:36–01:44 | Experiments: every configuration sees<br>the same 1,540 frozen cases. | MEASURED | media/work/captures-final/experiments.webm → processed local capture; source offset 0 s after startup trim | `docs/experiment_report.md`, `docs/release_recommendation.md` |
| 01:44–01:52 | gemini-3.8-flash macro F1: 0.885.<br>The release floor is 0.893. | MEASURED | media/work/captures-final/experiments.webm → processed local capture; source offset 8 s after startup trim | `docs/release_recommendation.md` |
| 01:52–02:00 | 4 sensitive intents miss the 0.95 recall gate.<br>The lowest is 0.60. | MEASURED | media/work/captures-final/experiments.webm → processed local capture; source offset 12 s after startup trim | `docs/release_recommendation.md` |
| 02:00–02:08 | Decision Policy: deterministic routing.<br>Edit the cohort, then preview its release gates. | MEASURED | media/work/captures-final/policy.webm → processed local capture; source offset 0 s after startup trim | `docs/release_recommendation.md` |
| 02:08–02:15 | Preview uses frozen results.<br>The app owner proposes the cohort for release. | MEASURED | media/work/captures-final/policy.webm → processed local capture; source offset 8 s after startup trim | `docs/release_recommendation.md` |
| 02:15–02:21 | Shadow: 85.5% label agreement over 1,540 cases. | SIMULATED | media/work/captures-final/shadow.webm → processed local capture; source offset 0 s after startup trim | `docs/release_recommendation.md` |
| 02:21–02:27 | $1.65 of measured model spend in shadow. | MEASURED | media/work/captures-final/shadow.webm → processed local capture; source offset 6 s after startup trim | `docs/release_recommendation.md` |
| 02:27–02:33 | +151 USD net value over 14 days<br>for the cohort versus the classifier. | ASSUMPTION | media/work/captures-final/shadow.webm → processed local capture; source offset 12 s after startup trim | `docs/release_recommendation.md` |
| 02:33–02:43 | Release: 5 of 10 full-candidate gates pass;<br>4 of 6 proposed-cohort gates pass. | MEASURED | media/live/triage-release-dark.png (numeric redaction overlay) | `docs/release_recommendation.md` |
| 02:43–02:51 | Activate full is blocked because release gates fail. | MEASURED | media/work/captures-final/policy.webm → processed local capture; source offset 15 s after startup trim | `docs/release_recommendation.md` |
| 02:51–02:58 | A governance admin records Withhold with a rationale. | MEASURED | media/work/captures-final/policy.webm → processed local capture; source offset 22 s after startup trim | `docs/release_recommendation.md` |
| 02:58–03:04 | Monitoring: the incident opened on simulated day 10. | FIXTURE; MEASURED | media/work/captures-final/monitoring.webm → processed local capture; source offset 0 s after startup trim | `docs/incident_report.md` |
| 03:04–03:10 | Review rate: 0.2177 against 0.2172.<br>Breach margin: 0.0006. | SIMULATED; FIXTURE; MEASURED | media/work/captures-final/monitoring.webm → processed local capture; source offset 6 s after startup trim | `docs/incident_report.md` |
| 03:10–03:16 | Incidents: drift detected the day it began.<br>Automation paused; rollback restores human review. | FIXTURE; MEASURED | media/work/captures-final/incidents.webm → processed local capture; source offset 0 s after startup trim | `docs/incident_report.md` |
| 03:16–03:22 | The drill records recovery. Automation resumed day 13. | FIXTURE; MEASURED | media/work/captures-final/incidents.webm → processed local capture; source offset 6 s after startup trim | `docs/incident_report.md` |
| 03:22–03:30 | Audit: trace lifecycle changes, actors,<br>reasons, and evidence references. | MEASURED | media/work/captures-extra/audit-top.png; real static Audit capture, with lower event rows masked to omit unapproved numeric prose | No numeric claim |
| 03:30–03:38 | Settings: admins manage roles.<br>Executive viewers have read-only access. | SYNTHETIC | media/work/captures-extra/settings.webm → processed local capture; source offset 1 s after startup trim | No numeric claim |
| 03:38–03:43 | IAP protects the console. Jobs produce durable evidence. | — | docs/diagrams/01_system_overview.png; reveal rectangles over the unchanged PNG | No numeric claim |
| 03:43–03:48 | Frozen evidence becomes a recorded release decision. | MEASURED | docs/diagrams/06_experiment_to_release.png; moving outline over the unchanged PNG | `docs/release_recommendation.md` |
| 03:48–03:56 | Keep the classifier authoritative.<br>Withhold gemini-3.8-flash. Reject gemini-3.1-flash-lite.<br>Limits: single-rater labels, simulated traffic, benchmark gap. | MEASURED | Typographic card; console tokens and local Inter | `docs/release_recommendation.md` |
| 03:56–04:00 | REPO_URL<br>Placeholder — owner to insert repository link | — | Typographic card; console tokens and local Inter | No numeric claim |

## README GIF

| Time | Every caption / title-card text | Provenance | Shot / source | Evidence |
|---|---|---|---|---|
| 00:00–00:08 | Pipeline: drag Mortgage Document Q&A into Evaluation.<br>Its approvals are in place. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 00:08–00:17 | Meeting Notes is blocked: the business case is missing. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 8 s after startup trim | No numeric claim |
| 00:17–00:23 | Executive viewer: write controls disappear. | SYNTHETIC | media/work/captures-final/pipeline.webm → processed local capture; source offset 17 s after startup trim | No numeric claim |
| 00:23–00:35 | Flow: see lifecycle movement and where apps stall. | SYNTHETIC | media/work/captures-final/flow.webm → processed local capture; source offset 0 s after startup trim | No numeric claim |
| 00:35–00:45 | Release: 5 of 10 full-candidate gates pass;<br>4 of 6 proposed-cohort gates pass. | MEASURED | media/live/triage-release-dark.png (numeric redaction overlay) | `docs/release_recommendation.md` |
| 00:45–00:53 | Activate full is blocked because release gates fail. | MEASURED | media/work/captures-final/policy.webm → processed local capture; source offset 15 s after startup trim | `docs/release_recommendation.md` |
| 00:53–01:00 | A governance admin records Withhold with a rationale. | MEASURED | media/work/captures-final/policy.webm → processed local capture; source offset 22 s after startup trim | `docs/release_recommendation.md` |

## Number audit

All factual numeral strings in captions are listed below. SRT cue indices/timestamps, model version identifiers, config identifiers, and diagram indices are metadata or identifiers. Exact string checks passed against the evidence files shown.

| Video | Time | Number as rendered | Label | Exact evidence |
|---|---|---|---|---|
| architecture | 00:24–00:28 | `1,540` | MEASURED | `docs/release_recommendation.md` |
| architecture | 00:28–00:31 | `5 of 10` | MEASURED | `docs/release_recommendation.md` |
| architecture | 00:50–00:56 | `5 of 10` | MEASURED | `docs/release_recommendation.md` |
| architecture | 00:50–00:56 | `1,540` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 01:18–01:27 | `0.849` | ASSUMPTION | `docs/business_case.md` |
| long-demo | 01:18–01:27 | `0.865` | ASSUMPTION | `docs/business_case.md` |
| long-demo | 01:18–01:27 | `0.864` | ASSUMPTION | `docs/business_case.md` |
| long-demo | 01:27–01:36 | `$57,270` | ASSUMPTION | `docs/business_case.md` |
| long-demo | 01:27–01:36 | `$66,957` | ASSUMPTION | `docs/business_case.md` |
| long-demo | 01:27–01:36 | `$62,130` | ASSUMPTION | `docs/business_case.md` |
| long-demo | 01:36–01:44 | `1,540` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 01:44–01:52 | `0.885` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 01:44–01:52 | `0.893` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 01:52–02:00 | `4` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 01:52–02:00 | `0.95` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 01:52–02:00 | `0.60` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 02:15–02:21 | `85.5%` | SIMULATED | `docs/release_recommendation.md` |
| long-demo | 02:15–02:21 | `1,540` | SIMULATED | `docs/release_recommendation.md` |
| long-demo | 02:21–02:27 | `$1.65` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 02:27–02:33 | `+151` | ASSUMPTION | `docs/release_recommendation.md` |
| long-demo | 02:27–02:33 | `14` | ASSUMPTION | `docs/release_recommendation.md` |
| long-demo | 02:33–02:43 | `5 of 10` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 02:33–02:43 | `4 of 6` | MEASURED | `docs/release_recommendation.md` |
| long-demo | 02:58–03:04 | `10` | FIXTURE; MEASURED | `docs/incident_report.md` |
| long-demo | 03:04–03:10 | `0.2177` | SIMULATED; FIXTURE; MEASURED | `docs/incident_report.md` |
| long-demo | 03:04–03:10 | `0.2172` | SIMULATED; FIXTURE; MEASURED | `docs/incident_report.md` |
| long-demo | 03:04–03:10 | `0.0006` | SIMULATED; FIXTURE; MEASURED | `docs/incident_report.md` |
| long-demo | 03:16–03:22 | `13` | FIXTURE; MEASURED | `docs/incident_report.md` |
| teaser | 00:03–00:07 | `5 of 10` | MEASURED | `docs/release_recommendation.md` |

The README GIF inherits the numeric captions from long-demo 00:18–00:51 and 02:33–02:58, with a two-second Flow freeze hold. In the source diagrams, approved frozen-set/gate/shadow figures retain their own provenance or the MEASURED caption; the schedule times and configuration-rule note containing unapproved extra parameters are masked. The preserved diagram indices, service-region name, model/config names, and metric names are identifiers.

## Editing and re-rendering

Caption sources: media/captions/teaser.srt, architecture_overview.srt, control_plane_demo.srt, and readme.srt. The matching Hyperframes HTML and storyboard JSON are under media/work/. `python3 media/work/caption_reburn.py architecture_overview --render` applies edited caption copy and re-runs the local check/render. Title-card text and editorial timing are edited directly in the composition/storyboard; the helper rejects changed SRT timings. Re-audit evidence after factual edits. For an edited demo render, run `python3 media/work/export_4min.py media/work/long-demo/control_plane_demo-edited.mp4` to regenerate MP4, WebM, the final numeric masks, and the GIF.

## Remaining owner action

Replace REPO_URL in the overview and long-demo compositions before any public release. Everything remains uncommitted; no uploads were performed. The local Studio draft preview is http://localhost:3002/#project/composition while its background server is running. Review the exported MP4/WebM for the final additional numeric masks in Reviews and Audit.

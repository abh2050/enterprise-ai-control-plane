# Asset manifest

Date: 2026-10-12 (America/Los_Angeles). Completed local production. The owner’s revised target is an exactly four-minute demo covering all major screens; it supersedes the original 7–8 minute specification. No AI-generated imagery or voice was used. Nothing was uploaded, committed, or pushed.

## Final deliverables

| File | Duration | Bytes | Resolution | Codec / format |
|---|---:|---:|---|---|
| media/teaser.mp4 | 21.000 s | 1,029,909 | 1920×1080 | h264; yuv420p; 30/1 fps; aac |
| media/teaser.webm | 21.008 s | 1,028,398 | 1920×1080 | vp9; yuv420p; 30/1 fps; opus |
| media/teaser.jpg | 0.040 s (still) | 180,032 | 1920×1080 | mjpeg; yuvj420p; 25/1 fps; silent |
| media/architecture_overview.mp4 | 58.000 s | 2,391,472 | 1920×1080 | h264; yuv420p; 30/1 fps; aac |
| media/architecture_overview.webm | 58.008 s | 2,061,879 | 1920×1080 | vp9; yuv420p; 30/1 fps; opus |
| media/control_plane_demo.mp4 | 240.000 s | 11,025,195 | 1920×1080 | h264; yuv420p; 30/1 fps; aac |
| media/control_plane_demo.webm | 240.008 s | 12,267,278 | 1920×1080 | vp9; yuv420p; 30/1 fps; opus |
| media/readme.gif | 60.000 s | 5,363,791 | 960×540 | gif; bgra; 25/2 fps; silent |

All MP4s: H.264, yuv420p, 30 fps, moov before mdat for faststart. WebM uses VP9 with Opus music. The 60-second GIF is 960×540 from a 12 fps source with centisecond GIF frame timings and a palette optimized for the cut. The teaser poster is the settled opening shot and is baked into frame zero.

## Tools and exact versions

- Hyperframes 0.8.150; local HTML/GSAP compositions and local screenshot rendering. Final checks: zero errors. Structural subcomposition warnings remain, with no runtime/layout errors. Final commands disable telemetry with HYPERFRAMES_NO_TELEMETRY=1.
- FFmpeg and ffprobe 9.0.2; H.264/VP9 encoding, faststart remux, palettegen/paletteuse GIF, metadata probes, and contact sheets.
- Playwright 1.64.0; Chromium 156.0.8078.4 for new product captures and caption layout checks.
- Hyperframes renderer Chrome headless shell 152.0.7977.30, Apple M3 Pro hardware GPU.
- Node v25.1.0; Python 3.14.4; GSAP 3.14.2. Local Inter variable font from the installed console package.
- Apple Swift 6.3.3 (swift-driver 1.148.6), Apple Vision OCR via the local helper for incidental numeral inspection. No remote model call.

## Music and license

Happy Beats & Business Moves Vol. 12 by Sascha Ende, bundled with brag. Gain 0.15, edge fades, repeated locally for the four-minute demo. No SFX and no voice. Official license checked 2026-10-12; public portfolio videos and commercial videos are permitted. Attribution is retained here even though the standard license says it is optional.

- Track: [Happy Beats & Business Moves Vol. 12](https://ende.app/en/song/12881-happy-beats-business-moves-vol-12)
- License: [ende.app standard license](https://ende.app/en/standard-license)
- Bundled source: /Users/abhishekshah/.claude/skills/brag/assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3

## Sources used

| Source | Use / treatment |
|---|---|
| media/live/triage-release-dark.png | Teaser, architecture, demo Release evidence; numeric masks |
| media/live/triage-monitoring-dark.png | Teaser incident evidence; numeric masks |
| media/live/incidents-dark.png | Architecture incident shot; numeric masks |
| media/work/captures-final/pipeline-blocked.png | Real blocked-move teaser still, copied into its composition assets |
| media/work/captures-final/pipeline.webm | Allowed drag, blocked drag, executive role switch; architecture and demo |
| media/work/captures-final/flow.webm | Flow Sankey and scroll |
| media/work/captures-final/business.webm | Business Case comparison and sensitivity table |
| media/work/captures-final/experiments.webm | Frozen scorecard and sensitive-intent evidence |
| media/work/captures-final/policy.webm | Cohort edit, gate preview, proposal, blocked full activation, Withhold record |
| media/work/captures-final/shadow.webm | Shadow economics and agreement |
| media/work/captures-final/monitoring.webm | Signals and drill detection |
| media/work/captures-final/incidents.webm | Incident timeline and recorded rollback/recovery |
| media/work/captures-extra/portfolio.webm | Portfolio overview and investment matrix |
| media/work/captures-extra/applications.webm | Directory search and filters |
| media/work/captures-review-success/reviews.webm | Actual governance-admin gate approval; routed-case section hidden |
| media/work/captures-extra/audit-top.png | Local DEMO audit trail still with sample identities; later numeric prose masked |
| media/work/captures-extra/settings.webm | Role management, then executive read-only restriction |
| docs/diagrams/01_system_overview.png | Unmodified original PNG; reveal rectangles and schedule-number masks |
| docs/diagrams/06_experiment_to_release.png | Unmodified original PNG; animated outline and extra-parameter mask |
| frontend/src/styles/tokens.css | Console colors and typography direction |
| frontend/node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2 | Local Inter font |
| https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js | Downloaded local runtime, no external rendering |

Evidence: docs/experiment_report.md, docs/release_recommendation.md, docs/business_case.md, docs/incident_report.md, data/registry_seed.json. Exact numeric strings and provenance labels are audited in docs/video_scripts.md and media/work/number_audit.json. The experiment report uses 1540; the recorded release rationale supplies the exact 1,540 spelling.

All original Section 4 sources were inventoried, including unused recordings: media/work/source_inventory.json and phase_0_inventory.md. The owner MOV was sampled only into an internal contact sheet; it appears in no final output. No customer case text, owner email, opened avatar menu, OAuth, browser chrome, or Mac menu bar appears in final media.

## Gates and review

- Phase 1: corrected the initial wrong-working-directory check, then the teaser check passed with zero errors; 21 seconds and within MP4/WebM limits. The earlier STOPPED_PHASE_1.md is historical and superseded.
- Phase 2: the final primary interactions captured successfully. The first Reviews take used Reviewer, which correctly could not approve Governance gates. A fresh take as Governance admin records the real approval. Earlier unsuccessful takes are retained as working files.
- Phase 3: architecture check passed with zero errors; 58 seconds and under 20 MB.
- Phase 4: four-minute demo check passed with zero errors; caption layout audit reports no captions over two lines. MP4/WebM and README GIF exported locally.
- Phase 5: timestamped scripts, SRT captions, numeric evidence audit, and this complete manifest produced.
- Phase 6: ffprobe gate passed for dimensions, codec, pixel format, frame rate, duration, size, and faststart. Contact sheets sampled every two seconds for the short videos and every ten seconds for the demo; all frames visually reviewed. Release and approval frames also checked at full resolution. Mode badges and DATA MODE remain visible.

Incidental metric numbers (including written-out counts), relative ages, axis ticks, and compact amounts were obscured to comply with the approved-number list. Approved numbers are burned into labelled captions; no invented replacement values. Header bars were pinned during scrolling captures with capture-only styles. The app, backend, source diagrams, fixtures, and raw footage were not changed. See video_scripts.md for editorial source offsets and the exact shot-by-shot captions.

REPO_URL remains an explicit placeholder in the architecture and demo outro cards. The owner must replace it before public release. No upload is needed to satisfy the file-size limit. The local Studio draft preview is http://localhost:3002/#project/composition while its background server is running. The exported MP4/WebM additionally apply final privacy/numeric masks to Reviews and the static Audit shot; use the exported files for final review.

## Every produced working file

Working files are retained under ignored media/work/. Earlier drafts and failed-take evidence are intentionally preserved. Text/code/font/binary helper files have no playback duration or image resolution. Renderer transient caches are not deliverables. Complete machine-readable metadata is in media/work/produced_file_inventory.json.

| Path | Duration | Bytes | Resolution | Codec / type |
|---|---:|---:|---|---|
| media/work/STOPPED_PHASE_1.md | — | 2,885 | — | md |
| media/work/__pycache__/build_videos.cpython-314.pyc | — | 26,233 | — | pyc |
| media/work/__pycache__/caption_reburn.cpython-314.pyc | — | 5,714 | — | pyc |
| media/work/__pycache__/write_caption_sources.cpython-314.pyc | — | 4,404 | — | pyc |
| media/work/architecture/brief.md | — | 789 | — | md |
| media/work/architecture/check-final.json | — | 12,877 | — | json |
| media/work/architecture/check-final.stderr | — | 176 | — | stderr |
| media/work/architecture/check-fixed.json | — | 12,877 | — | json |
| media/work/architecture/check-fixed.stderr | — | 176 | — | stderr |
| media/work/architecture/check.json | — | 16,052 | — | json |
| media/work/architecture/check.stderr | — | 719 | — | stderr |
| media/work/architecture/composition/assets/gsap.min.js | — | 72,779 | — | js |
| media/work/architecture/composition/assets/incidents-live.png | — | 274,889 | 1920×1080 | png |
| media/work/architecture/composition/assets/inter.woff2 | — | 48,256 | — | woff2 |
| media/work/architecture/composition/assets/monitoring-live.png | — | 308,543 | 1920×1080 | png |
| media/work/architecture/composition/assets/music.mp3 | 117.360 s | 2,817,792 | audio | mp3 |
| media/work/architecture/composition/assets/pipeline.mp4 | 22.900 s | 662,216 | 1920×1080 | h264 |
| media/work/architecture/composition/assets/release-flow.png | — | 491,805 | 3622×1578 | png |
| media/work/architecture/composition/assets/release-live.png | — | 335,833 | 1920×1080 | png |
| media/work/architecture/composition/assets/system.png | — | 512,805 | 3542×2230 | png |
| media/work/architecture/composition/hyperframes.json | — | 62 | — | json |
| media/work/architecture/composition/index.html | — | 10,674 | — | html |
| media/work/architecture/composition/package.json | — | 224 | — | json |
| media/work/architecture/overview-render.mp4 | 58.000 s | 2,391,784 | 1920×1080 | h264+aac |
| media/work/architecture/probe.json | — | 432 | — | json |
| media/work/architecture/render.log | — | 38,611 | — | log |
| media/work/architecture/storyboard.json | — | 3,677 | — | json |
| media/work/brag-output-2026-10-12/brag-final.jpg | — | 180,032 | 1920×1080 | mjpeg |
| media/work/brag-output-2026-10-12/brag-plan.md | — | 3,200 | — | md |
| media/work/brag-output-2026-10-12/brag-redacted.mp4 | 21.000 s | 1,105,326 | 1920×1080 | h264+aac |
| media/work/brag-output-2026-10-12/brag-render.mp4 | 21.000 s | 1,129,503 | 1920×1080 | h264+aac |
| media/work/brag-output-2026-10-12/brag.jpg | — | 180,032 | 1920×1080 | mjpeg |
| media/work/brag-output-2026-10-12/brag.mp4 | 21.000 s | 1,029,909 | 1920×1080 | h264+aac |
| media/work/brag-output-2026-10-12/check-final.json | — | 7,414 | — | json |
| media/work/brag-output-2026-10-12/check-final.stderr | — | 176 | — | stderr |
| media/work/brag-output-2026-10-12/check-resumed.json | — | 7,414 | — | json |
| media/work/brag-output-2026-10-12/check-resumed.stderr | — | 176 | — | stderr |
| media/work/brag-output-2026-10-12/check.json | — | 152 | — | json |
| media/work/brag-output-2026-10-12/check.stderr | — | 163 | — | stderr |
| media/work/brag-output-2026-10-12/composition/assets/blocked.png | — | 361,029 | 1920×1080 | png |
| media/work/brag-output-2026-10-12/composition/assets/gsap.min.js | — | 72,779 | — | js |
| media/work/brag-output-2026-10-12/composition/assets/inter.woff2 | — | 48,256 | — | woff2 |
| media/work/brag-output-2026-10-12/composition/assets/monitoring.png | — | 308,543 | 1920×1080 | png |
| media/work/brag-output-2026-10-12/composition/assets/music.mp3 | 117.360 s | 2,817,792 | audio | mp3 |
| media/work/brag-output-2026-10-12/composition/assets/release.png | — | 335,833 | 1920×1080 | png |
| media/work/brag-output-2026-10-12/composition/hyperframes.json | — | 188 | — | json |
| media/work/brag-output-2026-10-12/composition/index.html | — | 4,693 | — | html |
| media/work/brag-output-2026-10-12/composition/package.json | — | 223 | — | json |
| media/work/brag-output-2026-10-12/composition-brief.md | — | 1,514 | — | md |
| media/work/brag-output-2026-10-12/render-final.log | — | 15,040 | — | log |
| media/work/brag-output-2026-10-12/render.log | — | 16,096 | — | log |
| media/work/brag-output-2026-10-12/share-copy.txt | — | 191 | — | txt |
| media/work/build_4min.py | — | 6,590 | — | py |
| media/work/build_documents.py | — | 8,309 | — | py |
| media/work/build_videos.py | — | 18,246 | — | py |
| media/work/caption-layout-audit.json | — | 11,354 | — | json |
| media/work/caption_reburn.py | — | 3,023 | — | py |
| media/work/capture-numeric-audit.jsonl | — | 542 | — | jsonl |
| media/work/capture_extra.mjs | — | 3,554 | — | mjs |
| media/work/capture_final.mjs | — | 5,232 | — | mjs |
| media/work/capture_interactions.mjs | — | 5,169 | — | mjs |
| media/work/capture_interactions_v2.mjs | — | 5,325 | — | mjs |
| media/work/capture_review_success.mjs | — | 2,534 | — | mjs |
| media/work/capture_treatment.js | — | 3,060 | — | js |
| media/work/captures/business-detail.png | — | 356,781 | 1920×1080 | png |
| media/work/captures/business-lower.png | — | 215,442 | 1920×1080 | png |
| media/work/captures/business-top.png | — | 365,111 | 1920×1080 | png |
| media/work/captures/business.webm | 26.080 s | 6,482,593 | 1920×1080 | vp9 |
| media/work/captures/capture_log.json | — | 3,780 | — | json |
| media/work/captures/experiments-detail.png | — | 352,761 | 1920×1080 | png |
| media/work/captures/experiments-lower.png | — | 192,210 | 1920×1080 | png |
| media/work/captures/experiments-top.png | — | 358,480 | 1920×1080 | png |
| media/work/captures/experiments.webm | 26.240 s | 5,827,521 | 1920×1080 | vp9 |
| media/work/captures/flow-detail.png | — | 316,147 | 1920×1080 | png |
| media/work/captures/flow-error.png | — | 316,147 | 1920×1080 | png |
| media/work/captures/flow-top.png | — | 321,360 | 1920×1080 | png |
| media/work/captures/flow.webm | 48.080 s | 7,387,130 | 1920×1080 | vp9 |
| media/work/captures/incidents-top.png | — | 310,623 | 1920×1080 | png |
| media/work/captures/incidents.webm | 11.560 s | 1,611,134 | 1920×1080 | vp9 |
| media/work/captures/monitoring-detail.png | — | 333,616 | 1920×1080 | png |
| media/work/captures/monitoring-error.png | — | 333,616 | 1920×1080 | png |
| media/work/captures/monitoring-top.png | — | 339,329 | 1920×1080 | png |
| media/work/captures/monitoring.webm | 48.120 s | 8,161,198 | 1920×1080 | vp9 |
| media/work/captures/pipeline-allowed.png | — | 357,303 | 1920×1080 | png |
| media/work/captures/pipeline-blocked.png | — | 370,640 | 1920×1080 | png |
| media/work/captures/pipeline-executive.png | — | 339,623 | 1920×1080 | png |
| media/work/captures/pipeline-start.png | — | 354,432 | 1920×1080 | png |
| media/work/captures/pipeline.webm | 27.160 s | 5,881,666 | 1920×1080 | vp9 |
| media/work/captures/policy-activation-blocked.png | — | 345,638 | 1920×1080 | png |
| media/work/captures/policy-preview.png | — | 313,897 | 1920×1080 | png |
| media/work/captures/policy-proposed.png | — | 322,901 | 1920×1080 | png |
| media/work/captures/policy-thresholds.png | — | 319,961 | 1920×1080 | png |
| media/work/captures/policy-withhold-form.png | — | 350,398 | 1920×1080 | png |
| media/work/captures/policy-withhold-recorded.png | — | 253,854 | 1920×1080 | png |
| media/work/captures/policy.webm | 32.760 s | 5,846,964 | 1920×1080 | vp9 |
| media/work/captures/release-detail.png | — | 371,300 | 1920×1080 | png |
| media/work/captures/release-lower.png | — | 237,978 | 1920×1080 | png |
| media/work/captures/release-top.png | — | 378,389 | 1920×1080 | png |
| media/work/captures/release.webm | 26.160 s | 6,197,977 | 1920×1080 | vp9 |
| media/work/captures/run.log | — | 438 | — | log |
| media/work/captures/shadow-detail.png | — | 354,381 | 1920×1080 | png |
| media/work/captures/shadow-error.png | — | 354,381 | 1920×1080 | png |
| media/work/captures/shadow-top.png | — | 360,372 | 1920×1080 | png |
| media/work/captures/shadow.webm | 48.120 s | 8,460,193 | 1920×1080 | vp9 |
| media/work/captures-extra/applications-filtered.png | — | 249,282 | 1920×1080 | png |
| media/work/captures-extra/applications-top.png | — | 378,892 | 1920×1080 | png |
| media/work/captures-extra/applications.webm | 17.320 s | 2,562,460 | 1920×1080 | vp9 |
| media/work/captures-extra/audit-detail.png | — | 350,043 | 1920×1080 | png |
| media/work/captures-extra/audit-top.png | — | 384,114 | 1920×1080 | png |
| media/work/captures-extra/audit.webm | 15.360 s | 3,610,238 | 1920×1080 | vp9 |
| media/work/captures-extra/capture_log.json | — | 1,302 | — | json |
| media/work/captures-extra/portfolio-matrix.png | — | 230,310 | 1920×1080 | png |
| media/work/captures-extra/portfolio-top.png | — | 342,963 | 1920×1080 | png |
| media/work/captures-extra/portfolio.webm | 18.520 s | 3,922,744 | 1920×1080 | vp9 |
| media/work/captures-extra/reviews-error.png | — | 357,031 | 1920×1080 | png |
| media/work/captures-extra/reviews-pending.png | — | 357,031 | 1920×1080 | png |
| media/work/captures-extra/reviews.webm | 9.360 s | 1,967,155 | 1920×1080 | vp9 |
| media/work/captures-extra/run.log | — | 84 | — | log |
| media/work/captures-extra/settings-readonly.png | — | 213,607 | 1920×1080 | png |
| media/work/captures-extra/settings-roles.png | — | 288,361 | 1920×1080 | png |
| media/work/captures-extra/settings.webm | 15.280 s | 1,584,594 | 1920×1080 | vp9 |
| media/work/captures-final/business-detail.png | — | 198,540 | 1920×1080 | png |
| media/work/captures-final/business-lower.png | — | 198,540 | 1920×1080 | png |
| media/work/captures-final/business-top.png | — | 356,798 | 1920×1080 | png |
| media/work/captures-final/business.webm | 24.680 s | 6,058,353 | 1920×1080 | vp9 |
| media/work/captures-final/capture_log.json | — | 3,383 | — | json |
| media/work/captures-final/experiments-detail.png | — | 164,189 | 1920×1080 | png |
| media/work/captures-final/experiments-lower.png | — | 144,886 | 1920×1080 | png |
| media/work/captures-final/experiments-top.png | — | 328,474 | 1920×1080 | png |
| media/work/captures-final/experiments.webm | 24.720 s | 4,981,146 | 1920×1080 | vp9 |
| media/work/captures-final/flow-detail.png | — | 158,350 | 1920×1080 | png |
| media/work/captures-final/flow-lower.png | — | 152,583 | 1920×1080 | png |
| media/work/captures-final/flow-top.png | — | 305,468 | 1920×1080 | png |
| media/work/captures-final/flow.webm | 24.640 s | 4,548,715 | 1920×1080 | vp9 |
| media/work/captures-final/incidents-detail.png | — | 284,127 | 1920×1080 | png |
| media/work/captures-final/incidents-lower.png | — | 284,127 | 1920×1080 | png |
| media/work/captures-final/incidents-top.png | — | 289,676 | 1920×1080 | png |
| media/work/captures-final/incidents.webm | 24.280 s | 3,254,444 | 1920×1080 | vp9 |
| media/work/captures-final/monitoring-detail.png | — | 317,067 | 1920×1080 | png |
| media/work/captures-final/monitoring-lower.png | — | 317,067 | 1920×1080 | png |
| media/work/captures-final/monitoring-top.png | — | 322,610 | 1920×1080 | png |
| media/work/captures-final/monitoring.webm | 24.320 s | 5,095,250 | 1920×1080 | vp9 |
| media/work/captures-final/pipeline-allowed.png | — | 347,629 | 1920×1080 | png |
| media/work/captures-final/pipeline-blocked.png | — | 361,029 | 1920×1080 | png |
| media/work/captures-final/pipeline-executive.png | — | 330,047 | 1920×1080 | png |
| media/work/captures-final/pipeline-start.png | — | 344,074 | 1920×1080 | png |
| media/work/captures-final/pipeline.webm | 28.160 s | 5,836,945 | 1920×1080 | vp9 |
| media/work/captures-final/policy-activation-blocked.png | — | 323,769 | 1920×1080 | png |
| media/work/captures-final/policy-preview.png | — | 299,095 | 1920×1080 | png |
| media/work/captures-final/policy-proposed.png | — | 308,070 | 1920×1080 | png |
| media/work/captures-final/policy-thresholds.png | — | 305,199 | 1920×1080 | png |
| media/work/captures-final/policy-withhold-form.png | — | 328,619 | 1920×1080 | png |
| media/work/captures-final/policy-withhold-recorded.png | — | 217,628 | 1920×1080 | png |
| media/work/captures-final/policy.webm | 33.920 s | 5,535,112 | 1920×1080 | vp9 |
| media/work/captures-final/release-detail.png | — | 225,354 | 1920×1080 | png |
| media/work/captures-final/release-lower.png | — | 214,621 | 1920×1080 | png |
| media/work/captures-final/release-top.png | — | 351,810 | 1920×1080 | png |
| media/work/captures-final/release.webm | 24.760 s | 6,109,754 | 1920×1080 | vp9 |
| media/work/captures-final/run.log | — | 22 | — | log |
| media/work/captures-final/shadow-detail.png | — | 138,579 | 1920×1080 | png |
| media/work/captures-final/shadow-lower.png | — | 134,650 | 1920×1080 | png |
| media/work/captures-final/shadow-top.png | — | 330,460 | 1920×1080 | png |
| media/work/captures-final/shadow.webm | 24.600 s | 5,064,983 | 1920×1080 | vp9 |
| media/work/captures-review-success/capture_log.json | — | 244 | — | json |
| media/work/captures-review-success/reviews-approved.png | — | 362,786 | 1920×1080 | png |
| media/work/captures-review-success/reviews-pending.png | — | 363,710 | 1920×1080 | png |
| media/work/captures-review-success/reviews.webm | 19.440 s | 3,682,083 | 1920×1080 | vp9 |
| media/work/captures-review-success/run.log | — | 0 | — | log |
| media/work/captures-v2/business-detail.png | — | 301,728 | 1920×1080 | png |
| media/work/captures-v2/business-lower.png | — | 209,760 | 1920×1080 | png |
| media/work/captures-v2/business-top.png | — | 357,805 | 1920×1080 | png |
| media/work/captures-v2/business.webm | 27.280 s | 6,538,907 | 1920×1080 | vp9 |
| media/work/captures-v2/capture_log.json | — | 3,777 | — | json |
| media/work/captures-v2/experiments-detail.png | — | 322,960 | 1920×1080 | png |
| media/work/captures-v2/experiments-lower.png | — | 144,886 | 1920×1080 | png |
| media/work/captures-v2/experiments-top.png | — | 328,474 | 1920×1080 | png |
| media/work/captures-v2/experiments.webm | 27.320 s | 5,154,059 | 1920×1080 | vp9 |
| media/work/captures-v2/flow-detail.png | — | 301,456 | 1920×1080 | png |
| media/work/captures-v2/flow-error.png | — | 301,456 | 1920×1080 | png |
| media/work/captures-v2/flow-top.png | — | 307,153 | 1920×1080 | png |
| media/work/captures-v2/flow.webm | 47.400 s | 6,986,426 | 1920×1080 | vp9 |
| media/work/captures-v2/incidents-top.png | — | 289,569 | 1920×1080 | png |
| media/work/captures-v2/incidents.webm | 11.760 s | 1,491,841 | 1920×1080 | vp9 |
| media/work/captures-v2/monitoring-detail.png | — | 317,067 | 1920×1080 | png |
| media/work/captures-v2/monitoring-error.png | — | 317,067 | 1920×1080 | png |
| media/work/captures-v2/monitoring-top.png | — | 322,610 | 1920×1080 | png |
| media/work/captures-v2/monitoring.webm | 47.920 s | 7,576,783 | 1920×1080 | vp9 |
| media/work/captures-v2/pipeline-allowed.png | — | 347,629 | 1920×1080 | png |
| media/work/captures-v2/pipeline-blocked.png | — | 361,029 | 1920×1080 | png |
| media/work/captures-v2/pipeline-executive.png | — | 330,047 | 1920×1080 | png |
| media/work/captures-v2/pipeline-start.png | — | 344,074 | 1920×1080 | png |
| media/work/captures-v2/pipeline.webm | 28.160 s | 5,806,581 | 1920×1080 | vp9 |
| media/work/captures-v2/policy-activation-blocked.png | — | 323,680 | 1920×1080 | png |
| media/work/captures-v2/policy-preview.png | — | 299,095 | 1920×1080 | png |
| media/work/captures-v2/policy-proposed.png | — | 308,331 | 1920×1080 | png |
| media/work/captures-v2/policy-thresholds.png | — | 305,199 | 1920×1080 | png |
| media/work/captures-v2/policy-withhold-form.png | — | 328,532 | 1920×1080 | png |
| media/work/captures-v2/policy-withhold-recorded.png | — | 217,189 | 1920×1080 | png |
| media/work/captures-v2/policy.webm | 33.920 s | 5,479,931 | 1920×1080 | vp9 |
| media/work/captures-v2/release-detail.png | — | 344,598 | 1920×1080 | png |
| media/work/captures-v2/release-lower.png | — | 214,621 | 1920×1080 | png |
| media/work/captures-v2/release-top.png | — | 351,810 | 1920×1080 | png |
| media/work/captures-v2/release.webm | 27.360 s | 5,924,306 | 1920×1080 | vp9 |
| media/work/captures-v2/run.log | — | 438 | — | log |
| media/work/captures-v2/shadow-detail.png | — | 324,391 | 1920×1080 | png |
| media/work/captures-v2/shadow-error.png | — | 324,391 | 1920×1080 | png |
| media/work/captures-v2/shadow-top.png | — | 330,460 | 1920×1080 | png |
| media/work/captures-v2/shadow.webm | 47.440 s | 7,835,451 | 1920×1080 | vp9 |
| media/work/contact/architecture/exact-01.jpg | — | 100,917 | 1920×1440 | mjpeg |
| media/work/contact/architecture/exact-02.jpg | — | 145,240 | 1920×1440 | mjpeg |
| media/work/contact/architecture/exact-03.jpg | — | 42,470 | 1920×1440 | mjpeg |
| media/work/contact/architecture/page-01.jpg | — | 109,072 | 1920×1440 | mjpeg |
| media/work/contact/architecture/page-02.jpg | — | 150,825 | 1920×1440 | mjpeg |
| media/work/contact/architecture/page-03.jpg | — | 49,542 | 1920×1440 | mjpeg |
| media/work/contact/control_plane_demo/page-01.jpg | — | 405,266 | 1936×1460 | mjpeg |
| media/work/contact/control_plane_demo/page-02.jpg | — | 350,137 | 1936×1460 | mjpeg |
| media/work/contact/readme/page-01.jpg | — | 246,928 | 1936×732 | mjpeg |
| media/work/contact/spots/audit-final.png | — | 399,643 | 1920×1080 | png |
| media/work/contact/spots/frame-01.png | — | 590,491 | 1920×1080 | png |
| media/work/contact/spots/frame-02.png | — | 610,265 | 1920×1080 | png |
| media/work/contact/spots/frame-03.png | — | 380,860 | 1920×1080 | png |
| media/work/contact/spots/frame-04.png | — | 364,087 | 1920×1080 | png |
| media/work/contact/spots/frame-05.png | — | 461,475 | 1920×1080 | png |
| media/work/contact/spots/frame-06.png | — | 520,379 | 1920×1080 | png |
| media/work/contact/spots/frame-07.png | — | 388,085 | 1920×1080 | png |
| media/work/contact/spots/frame-08.png | — | 275,624 | 1920×1080 | png |
| media/work/contact/spots/frame-09.png | — | 69,971 | 1920×1080 | png |
| media/work/contact/spots/reviews-mask-final.png | — | 600,339 | 1920×1080 | png |
| media/work/contact/teaser-every-2s.jpg | — | 119,594 | 1920×1440 | mjpeg |
| media/work/contact/teaser-final.jpg | — | 128,070 | 1920×1440 | mjpeg |
| media/work/contact/teaser.jpg | — | 133,679 | 1920×1440 | mjpeg |
| media/work/demo-pipeline-inspect.png | — | 347,998 | 1920×1080 | png |
| media/work/diagram-numbers.jsonl | — | 2,709 | — | jsonl |
| media/work/export-4min.log | — | 55 | — | log |
| media/work/export_4min.py | — | 1,982 | — | py |
| media/work/final-qa.log | — | 1,807 | — | log |
| media/work/final_manifest.py | — | 10,149 | — | py |
| media/work/final_output_probe.json | — | 1,807 | — | json |
| media/work/final_qa.py | — | 2,106 | — | py |
| media/work/final_verification_notes.json | — | 549 | — | json |
| media/work/hf-reference/AGENTS.md | — | 8,626 | — | md |
| media/work/hf-reference/CLAUDE.md | — | 8,626 | — | md |
| media/work/hf-reference/hyperframes.json | — | 318 | — | json |
| media/work/hf-reference/index.html | — | 1,378 | — | html |
| media/work/hf-reference/meta.json | — | 95 | — | json |
| media/work/hf-reference/package.json | — | 301 | — | json |
| media/work/inspect/blocked.png | — | 362,562 | 1920×1080 | png |
| media/work/inspect/owner-contact.jpg | — | 218,265 | 2000×1757 | mjpeg |
| media/work/inspect_block.mjs | — | 772 | — | mjs |
| media/work/inspect_demo.mjs | — | 559 | — | mjs |
| media/work/live-redacted/incidents-dark.png | — | 274,889 | 1920×1080 | png |
| media/work/live-redacted/incidents-dark.png.redactions.json | — | 4,390 | — | json |
| media/work/live-redacted/pipeline-dark.png | — | 331,580 | 1920×1080 | png |
| media/work/live-redacted/pipeline-dark.png.redactions.json | — | 3,963 | — | json |
| media/work/live-redacted/triage-monitoring-dark.png | — | 308,543 | 1920×1080 | png |
| media/work/live-redacted/triage-monitoring-dark.png.redactions.json | — | 4,235 | — | json |
| media/work/live-redacted/triage-release-dark.png | — | 335,833 | 1920×1080 | png |
| media/work/live-redacted/triage-release-dark.png.redactions.json | — | 7,422 | — | json |
| media/work/long-build.log | — | 78 | — | log |
| media/work/long-demo/check-4min.json | — | 14,742 | — | json |
| media/work/long-demo/check.json | — | 31,055 | — | json |
| media/work/long-demo/check.stderr | — | 176 | — | stderr |
| media/work/long-demo/composition/.thumbnails/v5_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_source_index.html_1920x1080_1920x1080_1791832368094_0.00.jpg | — | 29,888 | 1920×1080 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_108.00_35a2f279bc6194a5_0.jpg | — | 1,610 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_120.00_03ecde40daff115e_0.jpg | — | 2,130 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_132.00_0492b2712a119130_0.jpg | — | 1,727 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_144.00_c57d23e0917f9673_0.jpg | — | 2,297 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_15.00_7b56f0a88ff93063_0.jpg | — | 3,429 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_157.50_c92f419560f97622_0.jpg | — | 2,385 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_172.50_8e6d36fbf078020b_0.jpg | — | 1,827 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_187.50_3cb0e612d2951c23_0.jpg | — | 1,862 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_202.50_99bdfb0ddaca4e18_0.jpg | — | 2,072 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_217.50_bf0ec9f989d27a33_0.jpg | — | 2,540 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_25.00_d12fcbe713e522a2_0.jpg | — | 2,323 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_3.00.jpg | — | 2,494 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_36.00_2d18312a9f852231_0.jpg | — | 1,981 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_372.00_29d4a077351f6b18_0.jpg | — | 2,142 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_384.00_be709087a05cb1ce_0.jpg | — | 2,136 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_441.00_8acc754ed86f3d2e_0.jpg | — | 3,208 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_453.00_b57b0f726098dd26_0.jpg | — | 4,119 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_462.00_713881ed90650d0c_0.jpg | — | 1,922 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_48.50_ba957818f9bbb9a8_0.jpg | — | 2,221 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_5.00_9149dc074109f25b_0.jpg | — | 2,494 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_61.00_1018141df72ee0f5_0.jpg | — | 1,849 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_73.50_f79f7efd97a43b77_0.jpg | — | 1,918 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_85.00_2b554dbb587e6e6f_0.jpg | — | 1,750 | 240×135 | mjpeg |
| media/work/long-demo/composition/.thumbnails/v5_v3_94e1c2d1e9ae36c1_229de2c361f66245_jpeg_preview_index.html_1920x1080_240x135_1791832368094_96.00_1c2a24c5a7df95c0_0.jpg | — | 1,954 | 240×135 | mjpeg |
| media/work/long-demo/composition/.waveform-cache/peaks-v2_assets_music-loop.mp3_10608356-1791832194019.json | — | 63,982 | — | json |
| media/work/long-demo/composition/.waveform-cache/v2_assets_music-loop.mp3_10608356-1791832194019.json | — | 76,412 | — | json |
| media/work/long-demo/composition/assets/applications.mp4 | 12.133 s | 250,335 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/audit.mp4 | 10.167 s | 584,299 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/business.mp4 | 19.500 s | 917,997 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/experiments.mp4 | 19.533 s | 765,536 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/flow.mp4 | 19.533 s | 622,050 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/gsap.min.js | — | 72,779 | — | js |
| media/work/long-demo/composition/assets/incidents-live.png | — | 274,889 | 1920×1080 | png |
| media/work/long-demo/composition/assets/incidents.mp4 | 19.133 s | 495,257 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/inter.woff2 | — | 48,256 | — | woff2 |
| media/work/long-demo/composition/assets/monitoring-live.png | — | 308,543 | 1920×1080 | png |
| media/work/long-demo/composition/assets/monitoring.mp4 | 19.133 s | 801,362 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/music-loop.mp3 | 464.931 s | 10,608,356 | audio | mp3 |
| media/work/long-demo/composition/assets/music.mp3 | 117.360 s | 2,817,792 | audio | mp3 |
| media/work/long-demo/composition/assets/pipeline.mp4 | 22.900 s | 662,216 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/policy.mp4 | 28.733 s | 696,681 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/portfolio.mp4 | 13.133 s | 425,601 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/release-flow.png | — | 491,805 | 3622×1578 | png |
| media/work/long-demo/composition/assets/release-live.png | — | 335,833 | 1920×1080 | png |
| media/work/long-demo/composition/assets/reviews.mp4 | 14.167 s | 399,793 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/settings.mp4 | 10.133 s | 182,005 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/shadow.mp4 | 19.467 s | 667,952 | 1920×1080 | h264 |
| media/work/long-demo/composition/assets/system.png | — | 512,805 | 3542×2230 | png |
| media/work/long-demo/composition/hyperframes.json | — | 62 | — | json |
| media/work/long-demo/composition/index.html | — | 22,413 | — | html |
| media/work/long-demo/composition/package.json | — | 221 | — | json |
| media/work/long-demo/demo-4min-render.mp4 | 240.000 s | 12,116,762 | 1920×1080 | h264+aac |
| media/work/long-demo/demo-render.mp4 | 465.000 s | 22,530,340 | 1920×1080 | h264+aac |
| media/work/long-demo/render-4min.log | — | 159,448 | — | log |
| media/work/long-demo/render.log | — | 284,091 | — | log |
| media/work/long-demo/storyboard-previous-465s.json | — | 11,750 | — | json |
| media/work/long-demo/storyboard.json | — | 9,839 | — | json |
| media/work/manifest-build.log | — | 58 | — | log |
| media/work/number_audit.json | — | 5,715 | — | json |
| media/work/ocr | — | 110,880 | — | file |
| media/work/ocr-test.json | — | 6,431 | — | json |
| media/work/ocr.swift | — | 1,255 | — | swift |
| media/work/ocr_words.swift | — | 1,247 | — | swift |
| media/work/phase_0_inventory.md | — | 15,343 | — | md |
| media/work/previous-4min-export/control_plane_demo.mp4 | 240.000 s | 11,022,162 | 1920×1080 | h264+aac |
| media/work/previous-4min-export/control_plane_demo.webm | 240.008 s | 12,263,417 | 1920×1080 | vp9+opus |
| media/work/qa_compositions.mjs | — | 1,086 | — | mjs |
| media/work/readme-palette.png | — | 808 | 16×16 | png |
| media/work/readme-source.mp4 | 60.000 s | 790,340 | 960×540 | h264 |
| media/work/readme-storyboard.json | — | 2,382 | — | json |
| media/work/redact_stills.mjs | — | 1,081 | — | mjs |
| media/work/source_inventory.json | — | 72,240 | — | json |
| media/work/write_caption_sources.py | — | 2,128 | — | py |
| media/captions/architecture_overview.srt | — | 1,217 | — | srt |
| media/captions/control_plane_demo.srt | — | 3,590 | — | srt |
| media/captions/readme.srt | — | 730 | — | srt |
| media/captions/teaser.srt | — | 532 | — | srt |
| docs/video_scripts.md | — | 19,626 | — | md |
| media/work/produced_file_inventory.json | — | 58,207 | — | json |
| docs/asset_manifest.md | — | 39,210 | — | md |

## Higgsfield atmosphere images (index.html)

Generated 2026-10-12 with the Higgsfield API, model `higgsfield-ai/soul/v2/standard` (16:9, 1080p), by `scripts/generate_assets.py` from `configs/visual_assets.yaml`. Thirteen images in total (one API probe plus two takes for each of six slots), about 0.04 USD at the listed 0.0032 USD per image. Atmosphere only: every image was reviewed for text, people, logos, and user interface before use; `evidence-2.png` was rejected because it contains glyph-like marks.

Terms checked 2026-10-12: Higgsfield's help center says users own their generations and may use them commercially, citing Section 4.4 of its Terms of Use ([who owns my generations](https://higgsfield.ai/creator-hub/help-center/account/who-owns-my-generations-and-can-i-use-them-commercially)). Originals (about 4 MB each) stay local in `assets/generated/` and are not committed; `assets/generated/manifest.json` (prompt, request id, timestamp) is. The site uses WebP versions at 1920 and 960 px in `assets/web/`.

| Web file | Source take | Use | Prompt |
|---|---|---|---|
| `assets/web/hero.webp` | `assets/generated/hero-2.png` | Hero background behind the headline and the teaser video | wide abstract space of thin luminous lines forming a series of open gates receding into darkness, one gate softly lit in cool blue, large empty dark area on the left, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens |
| `assets/web/decision.webp` | `assets/generated/decision-2.png` | Background band for "The decision" section | a single narrow beam of cool light stopped by a translucent glass threshold, the light pooling before it, dark graphite surroundings, quiet and deliberate, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens |
| `assets/web/evidence.webp` | `assets/generated/evidence-1.png` | Background band for the evidence and scorecard section | an orderly field of faint glowing measurement ticks and fine grid lines on dark graphite, a few cells gently illuminated, precise and quiet, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens |
| `assets/web/architecture.webp` | `assets/generated/architecture-2.png` | Background band for the architecture gallery | layered translucent planes stacked in depth like floors of a building, connected by thin vertical light threads, dark navy space, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens |
| `assets/web/incident.webp` | `assets/generated/incident-2.png` | Background band for the incident drill section | a calm dark horizon with one faint ripple of disturbance in the light, a soft pulse of cool light being contained by thin parallel lines, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens |
| `assets/web/closing.webp` | `assets/generated/closing-2.png` | Background for the author and links section | dawn-like soft cool glow rising over a dark minimal landscape of thin lines, open and hopeful, lots of empty space, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens |


## Landing page redesign: new sculptural imagery (2026-10-12)

Replaces the earlier atmosphere images on `index.html` with three new Higgsfield API generations. Art direction: monumental smoked glass, graphite, a precise blue light boundary, and a layered ontology sculpture. These are visual metaphors; the product captures and architecture diagrams remain implementation evidence.

- Provider / model: Higgsfield, `higgsfield-ai/soul/v2/standard`.
- API: `POST https://api.higgsfield.ai/higgsfield-ai/soul/v2/standard`; polled the returned status URL and downloaded the completed images.
- Inputs: 16:9, requested 1080p, one take per new asset. Returned originals: 2048 × 1152.
- Review: all three inspected visually; approved for this redesign. No people, logos, text, or fabricated interfaces.
- Web delivery: 1920 × 1080 WebP (quality 86) plus 960 × 540 (quality 82), responsive sources. Originals remain ignored; prompts, request IDs, and timestamps are tracked.
- Rights: [Higgsfield ownership and commercial-use guidance](https://higgsfield.ai/creator-hub/help-center/account/who-owns-my-generations-and-can-i-use-them-commercially), checked 2026-10-12.
- Reproduction: `uv run python scripts/generate_assets.py prism-control ontology-crystal release-barrier`. Completed takes are skipped. Credentials are read server-side from the environment or `.env`, never included in website assets.

### `prism-control`

- Web: `assets/web/prism-control.webp` and `assets/web/prism-control-960.webp`.
- Original: `assets/generated/prism-control-1.png`.
- Use: New landing page hero, sculptural control threshold.
- Request ID: `2acb1061-2cfd-4e37-9090-856be3401be9`.
- Generated: `2026-10-12T21:04:44+00:00`.
- Prompt: Architectural editorial photograph of a monumental smoked glass rectangular portal standing on a polished black basalt plinth, a brilliant narrow electric blue light plane precisely bisecting the glass, beautiful physical refraction and caustics, thick visible glass edges, centered sculptural object filling the right two thirds of the composition, left third empty ink black, low camera angle, vast black studio, luxury industrial design campaign, tactile materials, exquisite physically based rendering, dramatic chiaroscuro, sharp sculptural silhouette, not a tunnel, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens

### `ontology-crystal`

- Web: `assets/web/ontology-crystal.webp` and `assets/web/ontology-crystal-960.webp`.
- Original: `assets/generated/ontology-crystal-1.png`.
- Use: New ontology section artwork, related objects and shared structure.
- Request ID: `13590b21-0d52-475b-8210-50afd05e3115`.
- Generated: `2026-10-12T21:05:16+00:00`.
- Prompt: Museum quality product photograph of an exploded architectural glass sculpture, six substantial translucent smoked crystal rectangular blocks floating in an exact ordered vertical stack, hairline blue luminous filaments connecting the blocks, brushed titanium central spine, each block visibly distinct, reflections on a black obsidian base, three quarter camera view, sculpture centered with ample breathing room, hard rim light and rich black negative space, sophisticated Swiss industrial design aesthetic, photoreal materials and exquisite detail, no diagram, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens

### `release-barrier`

- Web: `assets/web/release-barrier.webp` and `assets/web/release-barrier-960.webp`.
- Original: `assets/generated/release-barrier-1.png`.
- Use: New decision section artwork, a deliberate release boundary.
- Request ID: `f3ecefbd-b5cc-4331-bcc9-4eb6933efdab`.
- Generated: `2026-10-12T21:05:48+00:00`.
- Prompt: Extreme close up architectural photograph of a single thick vertical smoked glass slab on black stone, an intense thin horizontal beam of icy blue light strikes the glass and refracts downward into a beautiful contained pool of light, precise hard edges and subtle fine surface detail, asymmetrical composition, strong visual tension at the point where the beam meets glass, luxury editorial still life, black background, physically plausible optical caustics, minimal monumental sculpture, cinematic, calm, minimal, deep navy and graphite palette, one cool blue accent glow, soft volumetric light, subtle film grain, no text, no letters, no numbers, no people, no faces, no logos, no user interface, no screens

### Additional presentation artifacts

- `assets/web/project-cover.webp`: browser capture of the redesigned local landing page, 1440 × 900, optimized as WebP for the README. Contains the new Higgsfield hero in its page context.
- `media/captions/control_plane_demo.vtt`: WebVTT conversion of the existing SRT captions for native HTML video accessibility. The four-minute film is unchanged.

Validation: all 9 product tabs, 7 ontology entities, and 13 diagram dialogs exercised in Chromium; keyboard tab navigation and Escape checked; 320, 390, 768, 1024, and 1440 px layouts have no page overflow. Video decoded with a 240.008-second duration and 31 caption cues. No page errors or failed local resource requests during the check.

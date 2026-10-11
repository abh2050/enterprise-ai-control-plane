# Enterprise AI Control Plane: Console Specification (Sections 9, 9A, 9B)

Received from the product owner on 2026-10-11. This specification replaces every earlier version of Section 9, 9A, and 9B. Build Section 9A first, then the pages in Section 9 on top of it, then install the visual layer from Section 9B.

## 9A. Design system and shell

Origin: This section adapts the structure, geometry, states, and interaction contracts of a sales CRM dashboard PRD. Build every component originally. Copy no code, screenshots, logos, or assets from any reference video. Visual diff checks compare against this project's own approved screens.

Use the frontend design skill before building any page.

### Shell

1. The reference viewport is 1440 by 900. The layout is desktop first and works down to 360 px.
2. The sidebar is 240 px wide with 24 px padding. It becomes an 80 px icon rail between 1024 and 1279 px, and a 56 px bottom navigation bar under 1024 px.
3. The top bar is 64 px high and sticky. It holds global search (slash key shortcut), the data mode badge (LIVE, SIMULATED, or FIXTURE), the date range picker, the platform filter, the theme toggle, and the avatar menu.
4. Every page shows a data mode banner. Seed data shows a SYNTHETIC banner.
5. The content pane uses 32 px horizontal and 28 px vertical padding, a 12 column grid with 24 px gutters, and a 1600 px maximum width.
6. Navigation order is Portfolio, Pipeline, Flow, Applications, Reviews, Incidents, Settings.
7. Routes encode every filter in the URL: /portfolio?range=&platform=, /pipeline?stage=all&owner=, /flow?range=, /apps?sort=recent, /apps/:appId?tab=, /reviews, /incidents. Opening a drawer never discards list state.

### Tokens

Palette name: Midnight Graphite with Signal Blue. Blue marks actions and selection. Green, amber, and red mark status only. Teal, violet, and slate serve charts only.

| Token | Dark | Light |
|---|---|---|
| bg_canvas | #0A0F1A | #F6F8FB |
| bg_surface | #111827 | #FFFFFF |
| bg_raised | #182233 | #EEF2F7 |
| bg_overlay | #1E2A3F | #FFFFFF |
| border | #26324A | #D8DFEA |
| border_strong | #34425E | #C3CEDD |
| text_primary | #EEF2F8 | #111827 |
| text_muted | #8C9AB0 | #5B677A |
| accent | #5B9BFF | #1F6FE0 |
| accent_strong | #3D7FF0 | #1858BF |
| accent_soft | #16294A | #E3EEFF |
| focus | #A8C8FF | #1A5BBF |
| status_healthy | #2FBF8F | #0F8A5F |
| status_warning | #F2B84B | #9A6700 |
| status_danger | #F0625F | #C23B3B |
| status_info | #7AB8FF | #2563EB |
| chart_1 | #5B9BFF | #1F6FE0 |
| chart_2 | #2DD4BF | #0F9488 |
| chart_3 | #A78BFA | #7C3AED |
| chart_4 | #F2B84B | #B7791F |
| chart_5 | #8C9AB0 | #64748B |
| hero_gradient_start | #0A0F1A | #F6F8FB |
| hero_gradient_end | #13233F | #DCE8FB |

Define each token as a CSS custom property with the same name. Charts use chart_1 through chart_5 in order and never use status colors for series. Verify every text pair at 4.5 to 1 contrast and every UI boundary at 3 to 1 under WCAG 2.2 AA, and adjust only failing values. The theme preference persists per user and switching themes triggers no data refetch.

Typography uses Inter with a Noto Sans fallback. Display is 32/38 at weight 700. Page titles are 24/30 at 700. Card titles are 14/20 at 600. Body text is 14/20 at 400. Labels are 12/16 at 600. KPI values are 30/36 at 700 with tabular numerals.

Spacing uses only 4, 8, 12, 16, 24, 32, 48, and 64 px. Cards use 24 px padding by default and 20 px in compact mode. Cards have a 12 px radius, controls have an 8 px radius, and pills are fully rounded. Base cards stay flat with a 1 px border. Only overlays get a shadow. The focus ring is 2 px with a 2 px offset.

Icons come from one outline set at 20 px for navigation and 16 px inline, with a 1.75 px stroke. Every icon only control has a tooltip and an accessible name. Status always pairs color with an icon and a text label.

Every metric shows a provenance badge: MEASURED, SIMULATED, FIXTURE, or ASSUMPTION.

### Number formatting

Compact formatting turns 1,000 into 1.0k and 1,000,000 into 1.0m. Tooltips and accessible labels show exact values. Percentages use one decimal and durations use whole days. Every card shows "Updated {relative time}" on hover and focus. Relative dates show the exact timestamp on hover and focus.

### Components and states

Every component implements these states: buttons (default, hover, focus, active, disabled, loading), inputs (empty, value, focus, error, disabled), KPI cards (loading, value, zero, error, stale), app cards (focus, menu open, dragging, conflict), drawers (opening, open, dirty, saving, error), toasts (success, warning, error, undo), and charts (loading, data, empty, error).

Loading uses fixed size skeletons with no layout shift. Empty states show a Section 9B illustration, explain what data is missing, and offer the action that fills it. A module error offers a retry while other modules stay usable. Data older than 5 minutes shows an amber timestamp with a refresh button.

### Charts

Charts keep at least 32 px left and 24 px bottom padding, use grid lines at 60% border opacity, use 11 px axis labels with at most six ticks, and use chart_1 for the primary series and chart_5 for comparisons. Every chart title states its conclusion. Every chart has labeled axes, a provenance badge, a hover tooltip with exact values and a click hint, and a table alternative.

### Motion

Hover and focus feedback takes 120 ms ease out. Card moves take 180 ms and drawers take 220 ms, both with cubic bezier (0.2, 0.8, 0.2, 1). KPI count transitions take 300 ms ease out. Charts animate for 240 ms on first paint and 160 ms on filter updates. Reduced motion settings remove movement, count animations, and video loops.

### Responsive behavior

At 1280 px and above the page uses the full 12 column grid. Between 1024 and 1279 px the grid drops to 8 columns and charts stack above lists. Between 720 and 1023 px KPIs show two per row and drawers take 70% of the viewport width. Under 720 px the layout becomes one column, detail views become full screen sheets, the Pipeline shows one stage at a time with a stage picker and a Move button, the investment matrix becomes a ranked list, and the catalog becomes a single column of cards. Touch targets are at least 44 by 44 px.

### Performance budgets

The initial shell loads with LCP at or under 2.5 seconds at p75. Portfolio API responses return within 600 ms at p95 for 1,000 apps. Initial route JavaScript stays at or under 250 KB gzipped, and charts load lazily. Optimistic updates render within 250 ms, server confirmation arrives within 2 seconds at p95, and background refresh runs every 60 seconds. All budgets must hold with the Section 9B assets present.

## 9. Pages

### Portfolio page

Purpose: An executive or governance lead opens one page and sees every AI project in the organization, how each one performs, and where investment should go next.

Layout at 1440 px:

| Module | Columns | Height | Priority |
|---|---|---|---|
| Header band (Section 9B) | 12 | 160 px | P1 |
| Apps in production KPI | 4 | 112 px | P0 |
| Monthly model spend KPI | 4 | 112 px | P0 |
| Governance Assist summary | 4 | 112 px | P0 |
| Secondary metrics strip | 12 | 48 px | P0 |
| Investment matrix | 8 | 296 px | P0 |
| Attention queue | 4 | 296 px | P0 |
| Platform breakdown | 8 | 208 px | P1 |
| Next gate deadline | 4 | 208 px | P1 |
| Portfolio catalog | 12 | flexible | P0 |

KPI formulas and click throughs:
1. Apps in production counts apps in the monitored stage. Clicking opens Pipeline filtered to monitored.
2. Monthly model spend sums settled attempt cost in the current month. Clicking opens a spend breakdown by app.
3. Value at risk sums estimated monthly value (ASSUMPTION) for apps with an assist score of 0.65 or higher. Clicking opens the Governance Assist drawer.

The secondary metrics strip shows total apps, stalled apps, estimated monthly value (ASSUMPTION), open incidents, and approvals waiting. Stalled apps are apps whose time in stage exceeds 1.5 times that stage's median. Each number links to a filtered view of the apps behind it.

The investment matrix plots each app by monthly cost on the x axis and estimated monthly value on the y axis. Bubble size shows monthly volume or active users. Bubble color shows risk tier with a matching shape. Quadrant labels read Scale, Fix, Watch, and Retire. Clicking a bubble opens the app drawer. Apps without value data appear in a "Needs business case" tray beside the chart.

The attention queue ranks the ten apps that most need action by assist score. Each row states the reason and the suggested action.

The platform breakdown shows a stacked bar chart of app counts and spend for Abacus, Copilot, custom, and managed apps.

The next gate deadline card counts down to the nearest expiring approval or scheduled review and links to that app.

The portfolio catalog shows a grid of app cards with a toggle to a dense table. Each card shows app name, owner, business unit, platform, lifecycle stage, risk tier, days in stage, monthly spend, a usage sparkline, health status, and the last governance decision. Filters cover platform, stage, risk tier, owner, business unit, health, and spend range. Sorting covers spend, value, days in stage, and last activity. Search matches app names, owners, and business problem text.

Health rules live in configs/lifecycle.yaml. An app is healthy when it has an owner, a business case, current approvals, spend within budget, and no open incident. It shows a warning when one of those conditions lapses. It shows danger when it has an open incident, exceeds its budget, or has no owner. The card tooltip names the rule that set the status.

A governance_admin can export the filtered catalog as CSV and the full page as PDF. CSV export escapes cells that begin with formula characters.

Exit check: a reviewer with no context can name the three most expensive apps, the riskiest app, and the app that most needs a decision within 60 seconds.

### Governance Assist

Governance Assist scores each app nightly and after every mutation with a deterministic rule set:

| Signal | Condition | Points |
|---|---|---|
| Stage stall | Days in stage exceed 1.5 times the stage median | +30 |
| Missing owner | The app has no active owner | +35 |
| Open incident | The app has an open incident | +35 |
| Budget pressure | Spend exceeds 90% of the monthly budget | +20 |
| Expiring approval | An approval expires within 14 days | +15 |
| Dormant app | The app has had no usage for 30 days | +15 |
| Recent evidence | A passing evaluation was recorded in the last 7 days | minus 15 |

The score equals total points divided by 100, clamped between 0 and 1. The threshold is 0.65. The system stores reason codes and an input snapshot with every score.

The collapsed card shows value at risk, app count, the top reason, and a Review apps button. The expanded drawer is 420 px wide on desktop and full screen under 720 px. Its header shows value, count, and scoring timestamp. Rows sort by score, then by spend, and show the app, its stage, its reasons with evidence, and a next action. The footer explains the scoring rules.

Schedule review opens a prefilled review request and saves nothing until the user confirms. Dismiss requires a reason and suppresses the same reason for seven days. Mark safe is limited to governance_admin, requires a note, and writes an audit event. Assist never changes a record silently. A failed action stays visible with a retry.

### Pipeline page

Columns follow the lifecycle stages: intake, business_case, review_gates, evaluation, shadow, controlled_activation, monitored, paused, retired. Each column is 280 px wide with a 16 px gap and a 48 px sticky header showing stage name, app count, and total monthly spend. The board scrolls horizontally inside the content pane.

App cards are at least 144 px tall with 16 px padding. Each card shows the app name (up to two lines), owner avatar, platform, risk tier, days in stage, a stall warning after 30 days, an assist dot, and a context menu with open, edit, move, and archive.

Dragging shows the card at 0.96 scale with a 12 px shadow. Valid drop targets get a 2 px accent outline and an accent_soft fill. Auto scroll starts within 48 px of an edge at up to 24 px per frame.

Each destination validates requirements before the move:
1. business_case requires volume, value hypothesis, and cost estimate.
2. review_gates requires a complete business case.
3. evaluation requires an approved review gate and a managed app config.
4. shadow requires a scorecard that passes all gates.
5. controlled_activation requires a recorded release decision.
6. monitored requires a publish decision or an activation.
7. retired requires a reason.
8. paused requires a reason, and paused apps can return only to their prior stage.

The server validates every move against configs/lifecycle.yaml and the user's role. A move sends the app's version number. The server updates the app inside a Firestore transaction and returns 409 with the current record if the version is stale. The conflict drawer offers "Use server version" or "Review and retry". The board moves the card optimistically, and one shared event reducer updates the Portfolio, Flow, and Pipeline caches. A failed move returns the card to its original column, names the reason in a toast, and returns focus to the card. Undo is available for 10 seconds.

Keyboard parity: Tab focuses cards, Space enters move mode, Left and Right arrows choose a stage, Enter confirms, Escape cancels, and a live region announces the result. Pointer and keyboard moves produce the same payload and audit event.

### Flow page

The header shows apps entered, apps reaching production, median days to production, and approval rate. Approval rate equals published apps divided by published plus rejected apps within the range, and its tooltip shows the formula, range, and population.

The page shows a Sankey chart of apps moving between stages over the selected period, a weekly in and out bar chart with the prior period as a 1 px comparison line, a table of median days in each stage, and a leaderboard of owners and business units by apps shipped, median cycle time, and spend. Clicking a Sankey link or a bar opens the filtered app list. BigQuery supplies this page's data, and the page shows the last export time.

### Applications page

The directory columns are name and business unit, owner, platform, stage, monthly spend, last activity, and next gate deadline. Search matches name, owner, and business problem text. Filters cover owner, platform, stage, and health. The default sort is most recently active.

The app drawer is 480 px wide. It shows the identity header with quick actions, key facts, the stage timeline, open incidents, and a governance notes composer fixed to the drawer bottom. Notes are plain text up to 5,000 characters, saved with Ctrl or Cmd plus Enter, stamped by the server with time and author, and protected from double submission by an idempotency key. Drafts persist locally for 24 hours. Authors can edit for 15 minutes with the prior version retained. Deletion is soft and requires a reason.

### App Detail page

The page opens from the drawer or the catalog and has these tabs:
1. Business Case: problem statement, assumptions, breakeven precision, and the sensitivity table.
2. Experiments: side by side comparison of the three configs with per intent drill down and bootstrap intervals.
3. Decision Policy: thresholds, sensitive intents, the cohort editor, and a confusion view filtered to sensitive intents.
4. Shadow: daily agreement, cost, and route comparisons, labeled SIMULATED.
5. Release: gate results with threshold and observed values, the decision form, the rationale, and decision history.
6. Monitoring: daily signal charts with alert lines.
7. Audit: the full event timeline.

External apps show only the Business Case, Monitoring, and Audit tabs.

### Reviews page

The page lists pending gate approvals and routed cases. Each item shows the evidence, the rubric, and the reason a different person must approve. The submitter's own items appear disabled with that explanation.

### Incidents page

The page lists open and closed incidents with signal, threshold, observed value, timeline, and actions taken. Open incidents switch the Portfolio header band to its incident variant.

### Snapshot mode

npm run build:snapshot builds the frontend against exported JSON files with no backend. The snapshot deploys to GitHub Pages so hiring managers can click through it. Snapshot mode shows a banner and disables every write control.

### Product analytics events

Send these events to BigQuery with app_id, user role, source view, and timestamp, and never with note text or personal data: portfolio_viewed, metric_drilldown_opened, assist_opened, assist_action_completed, app_drag_started, app_stage_change_completed, app_stage_change_failed, flow_filter_changed, app_drawer_opened, note_created, theme_changed.

### End to end scenarios

1. A user moves an app from review_gates to evaluation, and Portfolio and Flow update without reload.
2. Two users move the same app at once, and the second user sees the conflict drawer.
3. A user opens Governance Assist and schedules a review, and the score and deadline card update.
4. A user adds a governance note, and exactly one timeline entry appears after reload.
5. A user toggles the light theme, every token swaps, and the preference persists.
6. A keyboard only user completes a stage move with the same audit result as a drag.
7. A user applies platform and date filters, and every module reflects the same filter state.
8. A move to a stage with missing requirements is blocked, and the missing item is announced before any mutation.
9. An executive_viewer sees no write controls on any page.
10. Snapshot mode loads with no backend and exposes no write endpoint.

Visual validation captures 1440 by 900 at 100% zoom with fixed seed data and a fixed clock, in both themes, and compares against approved project screens at 0.5% pixel difference or less, excluding chart and text antialiasing.

## 9B. Generated visual layer with the Higgsfield API

Goal: The console and the showcase page must feel like a premium product. Higgsfield generates the atmosphere, motion, and illustration. Real data, real screenshots, and draw.io diagrams carry all evidence.

### Asset set

1. Sign in hero loop: a 6 to 8 second seamless loop at 1920 by 1080 behind the landing view and the snapshot site entry, with dark and light variants.
2. Page header bands: one 1440 by 160 seamless loop for each of Portfolio, Pipeline, Flow, Applications, Reviews, and Incidents. Portfolio shows a constellation of nodes. Pipeline shows lanes of moving light. Flow shows branching streams. Applications shows layered cards of light. Reviews shows a single focused beam. Incidents shows a pulsing amber field.
3. Incident ambience: a warning variant of the Portfolio band that appears only while an incident is open.
4. Empty state illustrations: eight stills at 640 by 400 for no apps, no incidents, no reviews, no experiments, no shadow runs, filters with no results, stale data, and first run onboarding.
5. Onboarding tour: four stills for a first visit tour of the Portfolio, Pipeline, Release, and Incidents views.
6. Video and showcase assets: title cards, chapter transitions, the closing card for both videos, and the hero loop for index.html.

### Art direction

Every prompt starts with the same fixed style prefix stored in configs/visual_assets.yaml. The prefix describes deep midnight graphite space, signal blue light (#5B9BFF) as the dominant glow, teal (#2DD4BF) and violet (#A78BFA) as secondary highlights, soft volumetric lighting, fine particle detail, slow and calm motion, and clean negative space on the left third for overlaid text. Every prompt forbids text, letters, numbers, logos, user interface elements, charts, and people. If the Higgsfield API supports seeds, reference images, or style presets, the generator fixes them across the whole set. Check the current Higgsfield API documentation before writing the client, and record the endpoint, model, and parameters in docs/asset_manifest.md.

### Generation pipeline

1. scripts/generate_assets.py reads configs/visual_assets.yaml, calls the Higgsfield API, and writes outputs to assets/generated/ with deterministic file names.
2. The script reads HIGGSFIELD_API_KEY from the environment. The key never ships to the browser, never enters Cloud Run, and never enters the repository.
3. The console never calls Higgsfield at runtime. All assets are generated once, reviewed, optimized, and committed.
4. A human reviews every asset in a contact sheet at assets/generated/review.html and marks it approved or rejected. Only approved assets enter the build.
5. The manifest logs each asset's prompt, model, parameters, date, file name, approval status, and intended use, plus the date the Higgsfield terms were checked for public portfolio use.
6. The cp assets command regenerates only rejected or missing assets, so approved assets never change by accident.

### Optimization budgets

1. Video loops ship as AV1 WebM with an H.264 MP4 fallback and a still poster in AVIF and WebP.
2. Header band loops stay under 1.5 MB each, the hero loop stays under 4 MB, and still illustrations stay under 150 KB each.
3. Loops play muted, inline, and without controls, and they pause when scrolled out of view.
4. Under prefers reduced motion, every loop shows its poster only.
5. Assets load lazily except the current page's header band.
6. Text over imagery sits on a scrim built from bg_canvas at 70% opacity so contrast holds at 4.5 to 1.

### Integrity rules

1. Generated imagery never depicts a dashboard, a chart, a metric, a product screenshot, a logo, a trademark, or a person presented as a user.
2. Platform identity for Abacus, Copilot, and custom builds uses neutral icons and text labels, never generated emblems that imitate a vendor brand.
3. Evidence on any page comes only from measured data, real screen recordings, and the draw.io diagrams.

## Milestone placement

M4 prompt: "Implement Section 9A first, then build the Section 9 pages on top of it. Add header band slots and empty state slots with placeholder posters from Section 9B." M4 exit check: all ten end to end scenarios pass, the lifecycle tests pass, and the visual validation passes in both themes.

M8 prompt: "Implement Section 9B in full before building index.html. Generate, review, optimize, and install every Higgsfield asset across the console, the snapshot site, index.html, and both videos." M8 exit check: every asset appears in the manifest as approved, the contact sheet shows a consistent palette and lighting, Lighthouse performance and accessibility stay at 90 or higher on mobile with assets present, reduced motion shows no moving imagery, and no HIGGSFIELD_API_KEY string appears in the repository, the container image, or the built frontend.

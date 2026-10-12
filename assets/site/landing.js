(() => {
  "use strict";
  const screens = [
    [
      "portfolio",
      "Portfolio",
      "INVESTMENT",
      "A portfolio with a point of view.",
      "KPIs, a cost-versus-value investment matrix, and an attention queue that names the next decision across the synthetic enterprise portfolio.",
    ],
    [
      "pipeline",
      "Pipeline",
      "LIFECYCLE",
      "Progress requires permission.",
      "Move applications through nine lifecycle stages. Drag-and-drop and keyboard actions run through the same server-side gate validation.",
    ],
    [
      "flow",
      "Flow analytics",
      "PORTFOLIO INTELLIGENCE",
      "See where momentum stops.",
      "Track how applications enter, advance, stall, and exit. The deployed system derives portfolio flow from BigQuery events.",
    ],
    [
      "triage-business",
      "Business case",
      "UNIT ECONOMICS",
      "Make the assumptions visible.",
      "Inspect breakeven precision and net-value sensitivity. Model performance is measured; volume, error costs, and projected value remain explicitly labeled assumptions.",
    ],
    [
      "triage-experiments",
      "Experiments",
      "MODEL EVALUATION",
      "Compare on the same ground.",
      "Three frozen configurations evaluated on the same 1,540 cases. Inspect per-intent results, bootstrap intervals, latency, and cost before choosing a candidate.",
    ],
    [
      "triage-policy",
      "Decision policy",
      "RELEASE CONSTRAINTS",
      "Define the bar before the launch.",
      "Preview how an eligible intent cohort changes the release gates. Sensitive-intent recall, quality, latency, and risk routing remain explicit constraints.",
    ],
    [
      "triage-release",
      "Release",
      "GOVERNANCE",
      "A decision you can explain.",
      "Every gate exposes its threshold, observed value, and result. The recorded decision and rationale explain why the LLM was withheld and the classifier retained.",
    ],
    [
      "triage-monitoring",
      "Monitoring",
      "OPERATING SIGNALS",
      "The release is only the beginning.",
      "Compare daily operating signals with frozen alert thresholds. Separate simulated traffic from the authored drift fixtures used in the incident drill.",
    ],
    [
      "incidents",
      "Incidents",
      "RECOVERY",
      "Close the loop when signals change.",
      "Follow the drill from detection to pause, rollback to human review, and recovery. Actions are attached to the application and recorded with an accountable actor.",
    ],
  ];
  const menu = document.querySelector(".tour-menu");
  const panel = document.querySelector("#screen-panel");
  function showScreen(index, focus = false) {
    const [id, name, category, title, copy] = screens[index];
    menu.querySelectorAll("button").forEach((button, i) => {
      button.setAttribute("aria-selected", String(index === i));
      button.tabIndex = index === i ? 0 : -1;
    });
    const image = document.querySelector("#screen-image");
    image.src = `assets/web/screens/${id}.webp`;
    image.alt = `${name} screen of the Enterprise AI Control Plane. ${copy}`;
    document.querySelector("#screen-zoom").href = image.getAttribute("src");
    document
      .querySelector("#screen-zoom")
      .setAttribute("aria-label", `View ${name} screenshot at full size`);
    document.querySelector("#screen-category").textContent = category;
    document.querySelector("#screen-title").textContent = title;
    document.querySelector("#screen-copy").textContent = copy;
    document.querySelector("#screen-count").textContent =
      `${String(index + 1).padStart(2, "0")} / 09`;
    panel.setAttribute("aria-labelledby", `screen-tab-${index}`);
    if (focus) menu.children[index].focus();
  }
  screens.forEach((screen, index) => {
    const button = document.createElement("button");
    button.className = "tour-tab";
    button.id = `screen-tab-${index}`;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "screen-panel");
    button.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span>${screen[1]}`;
    button.addEventListener("click", () => showScreen(index));
    button.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowDown" || event.key === "ArrowRight")
        next = (index + 1) % screens.length;
      if (event.key === "ArrowUp" || event.key === "ArrowLeft")
        next = (index + screens.length - 1) % screens.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = screens.length - 1;
      if (next !== undefined) {
        event.preventDefault();
        showScreen(next, true);
      }
    });
    menu.append(button);
  });
  showScreen(0);
  const compact = matchMedia("(max-width: 760px)");
  const orient = () =>
    menu.setAttribute(
      "aria-orientation",
      compact.matches ? "horizontal" : "vertical",
    );
  compact.addEventListener("change", orient);
  orient();
  const entities = {
    app: [
      "01",
      "THE OBJECT OF GOVERNANCE",
      "Application",
      "The stable anchor for ownership, risk, lifecycle stage, business assumptions, and the currently authoritative configuration.",
      [
        ["app_id", "Connects the application to its evidence and operations"],
        ["owner / stage", "Names accountability and lifecycle position"],
        ["active_config_id", "Identifies the authoritative configuration"],
      ],
      "Who owns this application, and what is allowed to run?",
    ],
    config: [
      "02",
      "THE REPRODUCIBLE VERSION",
      "Configuration",
      "A create-only model configuration binds a version, model, exact prompt hash, limits, price card, and policy. Evaluations refer to this configuration ID.",
      [
        ["config_id", "The version an experiment actually evaluated"],
        ["app_id", "The application this version belongs to"],
        ["policy_id", "The policy bound to the configuration"],
      ],
      "Which exact model and prompt produced this evidence?",
    ],
    policy: [
      "03",
      "THE EXPLICIT CONSTRAINTS",
      "Policy",
      "A create-only policy records thresholds, sensitive intents, and the eligible cohort. A release identifies the policy used for its decision.",
      [
        ["policy_id", "The policy referenced by configuration and release"],
        ["thresholds", "The quality and routing bars to satisfy"],
        ["eligible_cohort", "The intents a scoped activation can cover"],
      ],
      "What bar must this candidate clear before activation?",
    ],
    experiment: [
      "04",
      "THE EVALUATION EVIDENCE",
      "Experiment + Dataset",
      "An experiment links a frozen configuration to a pinned dataset. Per-case results capture prediction, routing, correctness, latency, tokens, and cost.",
      [
        ["config_id", "Which configuration was evaluated"],
        ["dataset_id", "Which source, commit, hash, and split were used"],
        ["metrics", "Values with units, provenance, and source"],
      ],
      "Can we trace the result back to its version and test data?",
    ],
    release: [
      "05",
      "THE RECORDED DECISION",
      "Release",
      "The release records the candidate, baseline, policy, scorecard, and observed gate results alongside the decision, rationale, actor, and time.",
      [
        [
          "candidate_config_id",
          "The proposed configuration; baseline is recorded too",
        ],
        ["policy_id", "The constraints used to judge the candidate"],
        ["decided_by", "The accountable decision maker"],
      ],
      "Why did this candidate advance—or stop?",
    ],
    incident: [
      "06",
      "THE OPERATIONAL RESPONSE",
      "Incident",
      "An incident belongs to an application and records the signal, threshold, observed value, status, actions, and timestamps for operational follow-through.",
      [
        ["app_id", "The affected application"],
        ["signal / observed", "What changed and what the monitor observed"],
        ["actions / status", "How the response progressed"],
      ],
      "What went wrong, which application was affected, and what happened next?",
    ],
    event: [
      "07",
      "THE ACCOUNTABILITY RECORD",
      "Review + AppEvent",
      "Create-only reviews capture gate or case decisions. Application events record lifecycle changes, actors, reasons, and evidence references.",
      [
        ["subject_id", "The gate or case a review addresses"],
        ["actor / reason", "Who changed application state and why"],
        ["evidence_refs", "The evidence attached to an application event"],
      ],
      "Who approved the action, and what evidence supported it?",
    ],
  };
  function showEntity(key) {
    const [index, kind, name, purpose, fields, question] = entities[key];
    for (const [id, value] of Object.entries({
      index,
      kind,
      name,
      purpose,
      question,
    }))
      document.getElementById(`entity-${id}`).textContent = value;
    const list = document.querySelector("#entity-fields");
    list.replaceChildren();
    fields.forEach(([key, description]) => {
      const row = document.createElement("div");
      const term = document.createElement("dt");
      term.textContent = key;
      const definition = document.createElement("dd");
      definition.textContent = description;
      row.append(term, definition);
      list.append(row);
    });
    document.querySelectorAll("[data-entity]").forEach((button) => {
      button.classList.toggle("active", button.dataset.entity === key);
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.entity === key),
      );
    });
  }
  document
    .querySelectorAll("[data-entity]")
    .forEach((button) =>
      button.addEventListener("click", () => showEntity(button.dataset.entity)),
    );
  showEntity("app");
  const diagrams = [
    ["01_system_overview", "System overview"],
    ["02_triage_request_path", "Triage request path"],
    ["03_registry_lifecycle", "Registry lifecycle"],
    ["04_identity_and_access", "Identity and access"],
    ["05_budget_ledger", "Budget ledger"],
    ["06_experiment_to_release", "Experiment to release"],
    ["07_analytics_pipeline", "Analytics pipeline"],
    ["08_monitoring_and_incident", "Monitoring and incident"],
    ["09_delivery", "Delivery"],
    ["10_local_development", "Local development"],
    ["11_public_demo", "Public demo"],
    ["12_bigquery_schema", "BigQuery schema"],
    ["13_data_lineage", "Data lineage"],
  ];
  const dialog = document.querySelector("#diagram-dialog");
  function openDiagram(id) {
    const name = diagrams.find((diagram) => diagram[0] === id)[1];
    document.querySelector("#diagram-title").textContent = name;
    const image = document.querySelector("#diagram-image");
    image.src = `docs/diagrams/${id}.png`;
    image.alt = `${name} architecture diagram`;
    document.querySelector("#diagram-source").href = image.getAttribute("src");
    dialog.showModal();
  }
  diagrams.forEach(([id, name], index) => {
    const button = document.createElement("button");
    button.className = "diagram-card";
    button.dataset.diagram = id;
    button.innerHTML = `<img src="assets/web/diagrams/${id}.webp" alt="" loading="lazy" width="1100" height="690"><span>${String(index + 1).padStart(2, "0")} / ${name} ↗</span>`;
    document.querySelector("#diagram-gallery").append(button);
  });
  document
    .querySelectorAll("[data-diagram]")
    .forEach((button) =>
      button.addEventListener("click", () =>
        openDiagram(button.dataset.diagram),
      ),
    );
  document
    .querySelector("#dialog-close")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (
      event.target === dialog &&
      (event.clientX < dialog.getBoundingClientRect().left ||
        event.clientX > dialog.getBoundingClientRect().right ||
        event.clientY < dialog.getBoundingClientRect().top ||
        event.clientY > dialog.getBoundingClientRect().bottom)
    )
      dialog.close();
  });
})();

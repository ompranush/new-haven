"use strict";
let featureAi = {},
  featureGod = {},
  settingsDirty = false,
  settingsLoaded = false;
function renderVillage() {
  const s = S.situation;
  if (!s) {
    $("#village-situation").innerHTML =
      '<p class="hint">Village observations are loading.</p>';
    return;
  }
  const w = s.wealth,
    r = s.relationships,
    p = s.politics,
    c = s.crime,
    e = s.equality;
  const fixed = (v, n = 1) =>
    v == null ? "Not yet observed" : Number(v).toFixed(n);
  const stat = (label, value, detail = "") =>
    '<div class="situation-stat"><span>' +
    esc(label) +
    "</span><strong>" +
    esc(value) +
    "</strong><small>" +
    esc(detail) +
    "</small></div>";
  const axis = (value, left, right) =>
    '<div class="opinion-axis"><div><span>' +
    esc(left) +
    "</span><span>" +
    esc(right) +
    '</span></div><div class="axis-track"><i style="left:' +
    clamp((num(value) + 1) * 50, 0, 100) +
    '%"></i></div><small>Mean preference ' +
    fixed(value, 2) +
    " · −1 to +1</small></div>";
  const counts = (groups) =>
    Object.entries(groups || {})
      .map(
        ([k, v]) =>
          '<span class="count-pill">' +
          esc(k) +
          " <strong>" +
          fmt(v) +
          "</strong></span>",
      )
      .join("");
  $("#village-situation").innerHTML =
    '<div class="ai-note">Village Situation is computed from this fictional world—not estimated by the language model. Political and crime behaviour use explicit toy-model rules; group differences are not evidence about real societies.</div><div class="situation-grid">' +
    '<div class="card situation-card"><span class="eyebrow">Distribution, not just totals</span><h2>Wealth & inequality</h2><div class="situation-stats">' +
    stat(
      "Citizen wealth",
      money(w.total),
      "Living residents; excludes council/business cash",
    ) +
    stat("Median wealth", money(w.median), "The middle resident") +
    stat("Gini coefficient", fixed(w.gini, 3), "0 equal · 1 concentrated") +
    stat(
      "Top 10% wealth share",
      fixed(w.top10_share) + "%",
      "Richest ceil(10% of residents)",
    ) +
    "</div></div>" +
    '<div class="card situation-card"><span class="eyebrow">Adult preferences · not an election</span><h2>Political leaning</h2>' +
    axis(p.economic_mean, "Collective provision", "Market-oriented") +
    '<div class="count-pills">' +
    counts(p.groups.economic) +
    "</div>" +
    axis(p.social_mean, "Liberal", "Traditional") +
    '<div class="count-pills">' +
    counts(p.groups.social) +
    '</div><details><summary>How these preferences change</summary><p class="hint">' +
    esc(p.explanation) +
    "</p></details></div>" +
    '<div class="card situation-card"><span class="eyebrow">The social fabric</span><h2>Relationships & belonging</h2><div class="situation-stats">' +
    stat("Friendship pairs", fmt(r.friendships), "Average recorded tie ≥40") +
    stat("Rivalry pairs", fmt(r.rivalries), "Average recorded tie ≤−20") +
    stat("Marriages", fmt(r.marriages), "Living partnerships") +
    stat(
      "Without close ties",
      fmt(r.isolated),
      "No friendship ≥40 and no spouse",
    ) +
    stat(
      "Mean relationship score",
      fixed(r.mean_trust),
      "−100 to +100; recorded living pairs",
    ) +
    '</div><p class="hint">Pairs are counted once. A missing relationship is not a negative relationship.</p></div>' +
    '<div class="card situation-card"><span class="eyebrow">Observed events · rolling window</span><h2>Crime & safety</h2><div class="situation-stats">' +
    stat(
      "Recorded thefts",
      fmt(c.incidents_30d),
      "Last " + fmt(c.observation_days) + " observed days (max 30)",
    ) +
    stat(
      "Incident rate",
      fixed(c.rate_per_1000_citizen_days, 2),
      "Per 1,000 observed citizen-days",
    ) +
    stat(
      "Money stolen",
      money(c.stolen_30d),
      "Transferred between residents, not destroyed",
    ) +
    '</div><details><summary>What this rate does—and does not—mean</summary><p class="hint">' +
    esc(c.explanation) +
    "</p></details></div>" +
    '<div class="card situation-card equality-card"><span class="eyebrow">Group outcomes, with context</span><h2>Gender equality & opportunity</h2><p>Equal job-based wage rules are enabled. The simulation does not use gender in hiring, pay, politics or crime risk. This is not a single “equality score”.</p><div class="situation-stats">' +
    stat(
      "Employment-rate gap",
      e.employment_gap == null
        ? "Insufficient groups"
        : fixed(e.employment_gap) + " pp",
      "Highest minus lowest adult group rate",
    ) +
    stat(
      "Group wealth ratio",
      e.wealth_ratio == null ? "Insufficient data" : fixed(e.wealth_ratio, 2),
      "Lowest / highest adult group mean",
    ) +
    '</div><div class="table-scroll"><table><thead><tr><th>Gender</th><th>Residents / adults</th><th>Employment</th><th>Mean adult wealth</th><th>Latest daily wage</th></tr></thead><tbody>' +
    e.groups
      .map(
        (g) =>
          "<tr><th>" +
          esc(g.gender) +
          "</th><td>" +
          fmt(g.population) +
          " / " +
          fmt(g.adults) +
          "</td><td>" +
          (g.employment_rate == null ? "—" : fixed(g.employment_rate) + "%") +
          "</td><td>" +
          (g.mean_wealth == null ? "—" : money(g.mean_wealth)) +
          "</td><td>" +
          (g.mean_daily_wage == null || !c.observation_days
            ? "Not observed"
            : money(g.mean_daily_wage)) +
          "</td></tr>",
      )
      .join("") +
    '</tbody></table></div><p class="hint">' +
    esc(e.explanation) +
    "</p></div></div>";
}
function updateFeatureControls() {
  const enabled =
    featureAi.enabled && num(featureAi.calls) < num(featureAi.max_calls);
  $("#god-interpret").disabled = busy || !enabled;
  $("#save-ai-settings").disabled = busy;
  $("#forget-ai").disabled = busy || !featureAi.configured;
  if ($("#god-confirm"))
    $("#god-confirm").disabled =
      busy || !featureGod.pending?.plan?.actions?.length;
  if ($("#god-cancel")) $("#god-cancel").disabled = busy;
}
function renderFeatureState(args, completedAction) {
  featureAi = args.ai || {};
  featureGod = args.god || {};
  if (["configure_ai", "forget_ai"].includes(completedAction) && !args.error)
    settingsDirty = false;
  if (!settingsLoaded || !settingsDirty) {
    const model = featureAi.model || "gpt-4.1-mini",
      known = ["gpt-4.1-mini", "gpt-4.1", "gpt-5-mini"].includes(model);
    $("#ai-model").value = known ? model : "custom";
    $("#custom-model").value = known ? "" : model;
    $("#custom-model-field").hidden = known;
    $("#ai-enable").checked = !!featureAi.enabled;
    $("#ai-call-limit").value = featureAi.max_calls || 10;
    settingsLoaded = true;
  }
  $("#settings-state").textContent =
    (featureAi.configured
      ? "Key saved for this session. "
      : "No API key configured. ") +
    "Model: " +
    featureAi.model +
    " · " +
    num(featureAi.calls) +
    " / " +
    num(featureAi.max_calls) +
    " calls used · " +
    fmt(featureAi.tokens) +
    " reported tokens. " +
    (featureAi.settings_notice || "");
  $("#god-access").textContent = featureAi.enabled
    ? "Interpreter: " +
      featureAi.model +
      " · " +
      Math.max(0, num(featureAi.max_calls) - num(featureAi.calls)) +
      " calls remaining. Simulation pauses while you write and preview commands."
    : "Open Settings to add your key, choose a model and enable explicit AI requests. No interpretation is performed without a key.";
  const pending = featureGod.pending;
  $("#god-preview").innerHTML = pending
    ? '<div class="command-preview"><span class="eyebrow">Review before applying</span><h3>' +
      esc(pending.plan.summary) +
      "</h3><ul>" +
      pending.preview.effects.map((t) => "<li>" + esc(t) + "</li>").join("") +
      "</ul>" +
      (pending.plan.limitations.length
        ? '<div class="crisis"><div><strong>Limitations / unsupported parts</strong><ul>' +
          pending.plan.limitations
            .map((t) => "<li>" + esc(t) + "</li>")
            .join("") +
          "</ul></div></div>"
        : "") +
      (pending.plan.actions.length
        ? '<p class="hint">Only the listed effects will happen. Applying uses no additional API call. Resource grants are explicit God-mode overrides, not earned income.</p><button id="god-confirm" class="primary">Apply these changes</button>'
        : "<p>No supported changes were proposed.</p>") +
      ' <button id="god-cancel">Discard preview</button></div>'
    : "";
  if ($("#god-confirm"))
    $("#god-confirm").onclick = () =>
      action("god_apply", { plan_id: pending.id });
  if ($("#god-cancel")) $("#god-cancel").onclick = () => action("god_cancel");
  $("#god-result").innerHTML = featureGod.result
    ? '<div class="goal"><strong>Applied on day ' +
      fmt(featureGod.result.day) +
      "</strong><ul>" +
      featureGod.result.effects.map((t) => "<li>" + esc(t) + "</li>").join("") +
      "</ul><button data-go-world>Inspect the world →</button></div>"
    : "";
  if ($("[data-go-world]"))
    $("[data-go-world]").onclick = () => setTab("world");
  updateFeatureControls();
  height();
}
function initializeFeatures() {
  $$("#ai-settings-form input, #ai-settings-form select").forEach((el) =>
    el.addEventListener("input", () => (settingsDirty = true)),
  );
  $("#ai-model").onchange = () =>
    ($("#custom-model-field").hidden = $("#ai-model").value !== "custom");
  $("#ai-settings-form").onsubmit = (e) => {
    e.preventDefault();
    if (busy) return;
    const api_key = $("#api-key").value;
    $("#api-key").value = "";
    action("configure_ai", {
      api_key,
      model:
        $("#ai-model").value === "custom"
          ? $("#custom-model").value.trim()
          : $("#ai-model").value,
      enabled: $("#ai-enable").checked,
      max_calls: Number($("#ai-call-limit").value),
    });
  };
  $("#forget-ai").onclick = () => {
    $("#api-key").value = "";
    action("forget_ai");
  };
  $("#god-interpret").onclick = () => {
    const command = $("#god-command").value.trim();
    if (!command) {
      toast("Describe a change first.");
      return;
    }
    playing = false;
    schedule();
    action("god_interpret", { command });
  };
  $$("[data-command]").forEach(
    (b) =>
      (b.onclick = () => {
        $("#god-command").value = b.dataset.command;
        $("#god-command").focus();
      }),
  );
  updateFeatureControls();
}

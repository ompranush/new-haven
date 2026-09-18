"use strict";
const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)],
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    ),
  num = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d),
  fmt = (v) => Math.round(num(v)).toLocaleString(),
  money = (v) => "£" + fmt(v),
  clamp = (v, a, b) => Math.min(b, Math.max(a, v));
let S = {
    citizens: [],
    buildings: [],
    businesses: [],
    events: [],
    history: [],
    terrain: [],
  },
  selected = null,
  activeTab = "world",
  playing = false,
  busy = false,
  sequence = 0,
  timer = null,
  oldPositions = new Map(),
  transitionStart = 0,
  lastSave = null,
  pendingId = null,
  pendingAction = null,
  receivedState = false;
function post(type, extra = {}) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...extra }, "*");
}
function action(action, data = {}) {
  if (busy) return;
  busy = true;
  updateControls();
  post("streamlit:setComponentValue", {
    value: { id: Date.now() + "-" + ++sequence, action, ...data },
  });
}
function toast(text) {
  $("#toast").textContent = text;
  $("#toast").style.display = "block";
  setTimeout(() => ($("#toast").style.display = "none"), 3500);
}
function schedule() {
  clearTimeout(timer);
  if (playing && !busy)
    timer = setTimeout(
      () => action("step", { days: 1 }),
      num($("#speed").value, 2500),
    );
}
function updateControls() {
  $("#play").textContent = playing ? "Ⅱ Pause" : "▶ Play";
  $("#live-status").textContent = busy
    ? "ADVANCING…"
    : playing
      ? "WORLD IN MOTION"
      : "PAUSED";
  [
    "#step",
    "#step10",
    "#intervene",
    "#reset",
    "#save",
    "#run-experiment",
  ].forEach((id) => ($(id).disabled = busy));
  renderIntervention();
  updateFeatureControls();
}
function setTab(tab) {
  activeTab = tab;
  if (["godmode", "settings"].includes(tab)) {
    playing = false;
    schedule();
    updateControls();
  }
  if (tab !== "settings") $("#api-key").value = "";
  $$(".section").forEach((el) => el.classList.toggle("active", el.id === tab));
  $$("nav button").forEach((el) =>
    el.classList.toggle("active", el.dataset.tab === tab),
  );
  $("#sidebar").classList.remove("open");
  $("#menu").setAttribute("aria-expanded", "false");
  const names = {
    world: [
      "The New Haven valley",
      "Follow a life. Change a policy. Watch the consequences.",
    ],
    citizens: [
      "The people of New Haven",
      "Individual lives. Shared possibilities.",
    ],
    economy: [
      "The whole village, in view",
      "Politics, belonging, opportunity, safety and shared prosperity.",
    ],
    chronicle: [
      "A history, still being written",
      "The moments that change a place and its people.",
    ],
    experiments: [
      "Explore another possibility",
      "Same beginning. Different choices. What changes?",
    ],
    godmode: [
      "God Mode",
      "Turn your intent into concrete, reviewable changes.",
    ],
    settings: [
      "AI settings",
      "Choose the model and control when your key is used.",
    ],
    guide: [
      "A field guide to living worlds",
      "A few ways to find your first story.",
    ],
  };
  $("#page-title").textContent = names[tab][0];
  $("#page-subtitle").textContent = names[tab][1];
  if (tab === "world") resize();
  height();
}
$$("[data-tab]").forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));
$("#menu").onclick = () => $("#sidebar").classList.toggle("open");
$("#play").onclick = () => {
  playing = !playing;
  updateControls();
  schedule();
};
$("#speed").onchange = schedule;
$("#step").onclick = () => action("step", { days: 1 });
$("#step10").onclick = () => action("step", { days: 10 });
$("#intervene").onclick = () =>
  action("intervene", { scenario: $("#intervention").value });
$("#reset").onclick = () => {
  playing = false;
  selected = null;
  action("reset", {
    seed: clamp(num($("#seed").value, 7), 0, 2147483647),
    population: clamp(num($("#population").value, 100), 20, 250),
  });
  schedule();
};
$("#save").onclick = () => action("save");
$("#load").onclick = () => $("#load-file").click();
$("#load-file").onchange = async (e) => {
  const file = e.target.files[0];
  if (file) {
    if (file.size > 15e6) {
      toast("Please choose a save file smaller than 15 MB.");
      return;
    }
    try {
      const data = await file.text();
      JSON.parse(data);
      playing = false;
      action("load", { data });
    } catch {
      toast("That file is not valid JSON.");
    }
  }
  e.target.value = "";
};
$("#run-experiment").onclick = () => {
  playing = false;
  schedule();
  action("experiment", {
    seeds: clamp(num($("#experiment-seeds").value, 3), 1, 10),
    horizon: clamp(num($("#experiment-horizon").value, 30), 14, 365),
    scenario: $("#experiment-scenario").value,
  });
  $("#experiment-results").innerHTML =
    '<p class="hint">Running paired worlds. This may take a moment…</p>';
};
$("#search").oninput = renderPeople;
$("#sort").onchange = renderPeople;
$("#event-search").oninput = renderEvents;
$("#event-kind").onchange = renderEvents;
function living() {
  return (S.citizens || []).filter((c) => c.alive !== false);
}
function citizen(id) {
  return (S.citizens || []).find((c) => String(c.id) === String(id));
}
function need(label, value) {
  value = clamp(num(value), 0, 100);
  return `<div class="need"><div><span>${esc(label)}</span><strong>${Math.round(value)}%</strong></div><div class="bar"><i style="width:${value}%;background:${value < 35 ? "#c87850" : "#699765"}"></i></div></div>`;
}
function renderInspector() {
  if (typeof worldView !== "undefined") worldView.setSelected(selected);
  const c = selected?.type === "citizen" ? citizen(selected.id) : null,
    b =
      selected?.type === "building"
        ? (S.buildings || []).find((b) => String(b.id) === String(selected.id))
        : null;
  if (b) {
    const biz = (S.businesses || []).find(
      (x) => x.id === b.id || (x.x === b.x && x.y === b.y),
    );
    $("#inspector").innerHTML =
      `<div class="eyebrow">Around the settlement</div><div class="avatar" style="margin-top:15px">${b.kind === "farm" ? "🌾" : b.kind === "mine" ? "⛰" : "⌂"}</div><h2>${esc(b.name || b.kind)}</h2><p>${esc(b.kind)}</p><hr class="separator"><p class="muted">Condition affects output. Builders repair damage over time using treasury funds, wood and stone.</p>${need("Building condition", b.condition ?? 100)}<p class="muted">Level ${fmt(b.level || 1)} · ${b.construction ? "Repairs in progress" : num(b.condition, 100) < 99 ? "Awaiting repair resources / workers" : "Operational"}</p>${biz ? `<div class="goal">${(biz.workers || []).length} workers · Cash ${money(biz.cash)}<br>Daily profit ${money(biz.profit)}</div>` : ""}<button id="clear-selection">Back to town overview</button>`;
    $("#clear-selection").onclick = () => {
      selected = null;
      renderInspector();
    };
    return;
  }
  if (!c) {
    $("#inspector").innerHTML =
      `<div class="eyebrow">A closer look</div><div class="avatar" style="margin-top:15px">♧</div><h2>Every dot is a life.</h2><p style="margin-top:9px">Choose a citizen to discover their hopes, memories, and connections.</p><hr class="separator"><div class="eyebrow">Town pulse</div>${need("Average happiness", S.happiness)}<div class="goal"><strong>${fmt(S.population)} neighbours</strong><br>${fmt(S.food)} food in the stores.<br>${money(S.treasury)} in the shared treasury.</div><p class="muted">Tip: pick someone and watch their story unfold as time passes.</p><button id="meet" style="margin-top:14px;width:100%">Meet a resident →</button>`;
    $("#meet").onclick = () => {
      if (living().length) {
        selected = { type: "citizen", id: living()[0].id };
        renderInspector();
      }
    };
    return;
  }
  const relationships = Object.entries(c.relationships || {})
      .sort((a, b) => num(b[1]) - num(a[1]))
      .slice(0, 4),
    memories = (c.memories || []).slice(-5).reverse();
  $("#inspector").innerHTML =
    `<div style="display:flex;justify-content:space-between"><div class="eyebrow">Resident journal</div><button class="link" id="clear-selection" aria-label="Close resident inspector">✕</button></div><div class="avatar" style="margin-top:14px">${num(c.age) < 18 ? "🧒" : num(c.age) > 65 ? "🧓" : "🧑"}</div><h2>${esc(c.name)}</h2><p class="muted">${esc(c.job || "Seeking work")} · Age ${Math.floor(num(c.age))}</p><p style="font-size:12px;margin-top:10px">${esc(c.activity || "Taking in the town")}</p><div class="goal"><span class="eyebrow">Working towards</span><br>${esc(c.goal || "A good life in New Haven")}<br><small>Progress ${fmt(c.goal_progress)}%</small></div>${need("Happiness", c.happiness)}${need("Health", c.health)}${need("Energy", c.energy)}${need("Food security", 100 - num(c.hunger))}<p class="muted">Savings <strong>${money(c.wealth)}</strong></p><hr class="separator"><div class="eyebrow">Personality</div><p class="muted">${
      Object.entries(c.personality || {})
        .map(
          ([k, v]) =>
            esc(k) +
            ": " +
            (typeof v === "number"
              ? Math.round(v * (v <= 1 ? 100 : 1)) + "%"
              : esc(v)),
        )
        .join(" · ") || "A character still unfolding"
    }</p><hr class="separator"><div class="eyebrow">Closest connections</div>${relationships.map(([id, score]) => `<p class="muted">${esc(citizen(id)?.name || "Former resident")} <strong>${Math.round(num(score))}</strong>${String(id) === String(c.partner_id) ? " ♥" : ""}</p>`).join("") || '<p class="muted">New friendships are yet to come.</p>'}<hr class="separator"><div class="eyebrow">Memories that stay</div>${memories.map((m) => `<div class="memory">${esc(typeof m === "string" ? m : m.text)}${typeof m === "object" ? `<small>Day ${esc(m.day)}</small>` : ""}</div>`).join("") || '<p class="muted">A fresh page. Advance time to begin.</p>'}`;
  $("#clear-selection").onclick = () => {
    selected = null;
    renderInspector();
  };
  height();
}
function renderMetrics() {
  const cards = [
    ["Residents", fmt(S.population), "Lives in the settlement"],
    [
      "Food stores",
      fmt(S.food),
      (num(S.food) / Math.max(1, num(S.population))).toFixed(1) +
        " days · £" +
        num(S.food_price).toFixed(2) +
        " / meal",
    ],
    ["Shared treasury", money(S.treasury), "Resources for tomorrow"],
    ["Happiness", fmt(S.happiness) + "%", "The mood of the town"],
    [
      "Materials",
      fmt(S.resources?.wood) + " / " + fmt(S.resources?.stone),
      "Wood / stone available for recovery",
    ],
    [
      "Employment",
      fmt(100 - num(S.unemployment)) + "%",
      "Among working-age citizens",
    ],
  ];
  $("#metrics").innerHTML = cards
    .map(
      ([label, value, sub]) =>
        `<div class="metric"><div class="eyebrow">${label}</div><div class="value">${value}</div><small>${sub}</small></div>`,
    )
    .join("");
  $("#day-label").textContent = "Day " + fmt(S.day);
  $("#weather-label").textContent =
    (S.season || "Spring") + " · " + (S.weather || "Clear");
  $("#map-label").textContent = "NEW HAVEN · SEED " + (S.seed ?? 7);
}
function renderPeople() {
  const q = $("#search").value.toLowerCase(),
    sort = $("#sort").value;
  let people = living().filter((c) =>
    [c.name, c.job, c.goal].join(" ").toLowerCase().includes(q),
  );
  people.sort((a, b) =>
    sort === "name"
      ? String(a.name).localeCompare(String(b.name))
      : sort === "health"
        ? num(a.health) - num(b.health)
        : num(b[sort]) - num(a[sort]),
  );
  $("#people-count").textContent = people.length + " residents";
  $("#people-grid").innerHTML =
    people
      .slice(0, 500)
      .map(
        (c) =>
          `<button class="card person" data-person="${esc(c.id)}"><div class="person-top"><div class="person-face">${num(c.age) < 18 ? "🧒" : num(c.age) > 65 ? "🧓" : "🧑"}</div><div><strong>${esc(c.name)}</strong><div class="muted">${esc(c.job || "Seeking work")} · ${Math.floor(num(c.age))}</div></div></div><div class="person-stat"><span>${esc(c.activity || "Exploring")}</span><strong>${money(c.wealth)}</strong></div>${need("Happiness", c.happiness)}</button>`,
      )
      .join("") || '<div class="empty">No citizens match that search.</div>';
  $$("[data-person]").forEach(
    (b) =>
      (b.onclick = () => {
        selected = { type: "citizen", id: b.dataset.person };
        setTab("world");
        renderInspector();
      }),
  );
  height();
}
function eventHtml(e) {
  if (typeof e === "string")
    return `<div class="event"><span class="event-icon">≋</span><div><p>${esc(e)}</p></div></div>`;
  const icon =
    {
      birth: "✧",
      death: "◈",
      marriage: "♡",
      storm: "☂",
      economy: "↗",
      social: "♧",
      politics: "⚑",
      education: "✎",
    }[e.kind] || "≋";
  return `<div class="event"><span class="event-icon">${icon}</span><div><h3>${esc(e.title || e.kind || "A moment in town")}</h3><p>${esc(e.text || e.description || "")}</p></div><time>Day ${esc(e.day ?? S.day)}</time></div>`;
}
function renderEvents() {
  const events = [...(S.events || [])].reverse(),
    q = $("#event-search").value.toLowerCase(),
    kind = $("#event-kind").value;
  $("#recent-events").innerHTML =
    events.slice(0, 3).map(eventHtml).join("") ||
    '<div class="empty">The town’s first chapter is waiting. Advance a day.</div>';
  const kinds = [
    ...new Set(
      events
        .filter((e) => typeof e === "object")
        .map((e) => e.kind)
        .filter(Boolean),
    ),
  ];
  $("#event-kind").innerHTML =
    '<option value="all">Every kind of story</option>' +
    kinds.map((k) => `<option value="${esc(k)}">${esc(k)}</option>`).join("");
  $("#event-kind").value = kinds.includes(kind) ? kind : "all";
  $("#all-events").innerHTML =
    events
      .filter(
        (e) =>
          (kind === "all" || e.kind === kind) &&
          JSON.stringify(e).toLowerCase().includes(q),
      )
      .slice(0, 250)
      .map(eventHtml)
      .join("") || '<div class="empty">No stories match this filter yet.</div>';
  height();
}
function chart(label, key, color) {
  const history = S.history || [],
    values = history.map((h) => num(h[key])),
    w = 480,
    h = 135,
    min = Math.min(...values, 0),
    max = Math.max(...values, 1),
    range = max - min,
    points = values
      .map(
        (v, i) =>
          `${28 + (i / Math.max(1, values.length - 1)) * (w - 40)},${h - 14 - ((v - min) / range) * (h - 30)}`,
      )
      .join(" ");
  return `<div class="card chart"><div class="eyebrow">${label}</div><div style="font-size:25px;margin-top:5px">${fmt(values.at(-1) ?? S[key])}</div><svg viewBox="0 0 480 165" role="img" aria-label="${label} over ${history.length} recorded days"><line x1="28" y1="121" x2="468" y2="121" stroke="#dce5dc"/><text x="28" y="155" font-size="11" fill="#516560">Day ${esc(history[0]?.day ?? 0)}</text><text x="468" y="155" text-anchor="end" font-size="11" fill="#516560">Day ${esc(history.at(-1)?.day ?? S.day ?? 0)}</text>${values.length > 1 ? `<polygon points="28,121 ${points} 468,121" fill="${color}" opacity=".1"/><polyline points="${points}" fill="none" stroke="${color}" stroke-width="2.5"/>` : '<text x="240" y="80" text-anchor="middle" fill="#516560" font-size="12">Advance time to reveal the trend</text>'}</svg></div>`;
}
function renderEconomy() {
  renderVillage();
  $("#charts").innerHTML =
    chart("Population", "population", "#447a58") +
    chart("Average happiness", "happiness", "#bd863e") +
    chart("Food reserves", "food", "#7b9348") +
    chart("Town treasury", "treasury", "#44898b");
  $("#businesses").innerHTML =
    (S.businesses || [])
      .map(
        (b) =>
          `<div class="card business"><span class="tag">${esc(b.kind || "Local business")}</span><h3>${esc(b.name)}</h3><p class="muted">${(b.workers || []).length} workers</p><div class="person-stat"><span>Cash ${money(b.cash)}</span><strong>Profit ${money(b.profit)}</strong></div></div>`,
      )
      .join("") ||
    '<div class="empty">Business records will appear here.</div>';
}
function renderExperiment(result) {
  if (!result) return;
  const metrics = [
    "population",
    "happiness",
    "food",
    "treasury",
    "unemployment",
  ];
  const a = result.aggregate;
  if (a) {
    $("#experiment-results").innerHTML =
      `<h3 style="margin-top:25px">${result.mode === "ai" ? "Rules vs. AI-assisted" : "One intervention, measured"} · ${esc(result.seeds)} seeds</h3><p class="muted">Mean outcomes after ${esc(result.horizon)} days per world</p><div style="overflow:auto"><table><thead><tr><th>Measure</th><th>World A · baseline</th><th>World B · ${esc(result.mode === "ai" ? "AI-assisted" : result.scenario)}</th><th>Difference</th></tr></thead><tbody>${metrics.map((k) => `<tr><th>${esc(k.replaceAll("_", " "))}</th><td>${num(a.baseline?.[k]).toFixed(1)}</td><td>${num(a.treatment?.[k]).toFixed(1)}</td><td>${num(a.delta?.[k]) > 0 ? "+" : ""}${num(a.delta?.[k]).toFixed(1)}</td></tr>`).join("")}</tbody></table></div><p class="hint">${esc(result.note || "Paired starting conditions help isolate the effect of a change. More seeds offer a broader view.")}</p><details style="margin-top:15px"><summary>See individual seed outcomes</summary><div style="overflow:auto"><table><thead><tr><th>Seed</th><th>Population A / B</th><th>Happiness A / B</th><th>Food A / B</th></tr></thead><tbody>${(result.runs || []).map((r) => `<tr><td>${esc(r.seed)}</td><td>${fmt(r.baseline?.population)} / ${fmt(r.treatment?.population)}</td><td>${fmt(r.baseline?.happiness)} / ${fmt(r.treatment?.happiness)}</td><td>${fmt(r.baseline?.food)} / ${fmt(r.treatment?.food)}</td></tr>`).join("")}</tbody></table></div></details>`;
  } else {
    $("#experiment-results").innerHTML =
      '<p class="hint">' + esc(result.note || "Experiment complete.") + "</p>";
  }
  const skipped = (result.runs || []).filter(
    (r) => result.mode !== "ai" && r.intervention_applied === false,
  );
  if (skipped.length)
    $("#experiment-results").insertAdjacentHTML(
      "afterbegin",
      '<div class="crisis">' +
        esc(
          skipped
            .map((r) => "Seed " + r.seed + ": " + r.intervention_note)
            .join(" · "),
        ) +
        " · These runs remain in the aggregate.</div>",
    );
  const weeks = (result.runs || []).filter((r) => r.impact_week);
  if (weeks.length && result.mode !== "ai") {
    const mean = (key) =>
      weeks.reduce((sum, r) => sum + num(r.impact_week[key]), 0) / weeks.length;
    $("#experiment-results").insertAdjacentHTML(
      "beforeend",
      '<div class="goal"><strong>One week after the scheduled intervention</strong><br>Mean food difference: ' +
        fmt(mean("food")) +
        " meals · Treasury difference: " +
        money(mean("treasury")) +
        ". This checkpoint exposes short-term costs that final outcomes can hide.</div>",
    );
  }
  if (result.runs?.length)
    $("#experiment-results").insertAdjacentHTML(
      "beforeend",
      '<div class="goal"><strong>Execution record</strong><br>' +
        result.runs
          .map(
            (r) =>
              "Seed " +
              esc(r.seed) +
              " · " +
              esc(
                result.mode === "ai"
                  ? num(r.ai_calls) + " actual AI calls"
                  : r.intervention_note,
              ),
          )
          .join("<br>") +
        "</div>",
    );
  height();
}
$("#load-file").onchange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 8e6) {
    toast("Please choose a save file smaller than 8 MB.");
    event.target.value = "";
    return;
  }
  try {
    const data = await file.text();
    JSON.parse(data);
    action("load", { data });
  } catch {
    toast("That file is not valid JSON.");
  }
  event.target.value = "";
};
$("#menu").setAttribute("aria-expanded", "false");
const closeMenu = document.createElement("button");
closeMenu.className = "mobile-toggle";
closeMenu.textContent = "Close menu ✕";
closeMenu.onclick = () => {
  $("#sidebar").classList.remove("open");
  $("#menu").setAttribute("aria-expanded", "false");
  $("#menu").focus();
};
$("#sidebar").prepend(closeMenu);
$("#menu").onclick = () => {
  const opened = $("#sidebar").classList.toggle("open");
  $("#menu").setAttribute("aria-expanded", String(opened));
  if (opened) closeMenu.focus();
};
const aiControl = document.createElement("label");
aiControl.style.cssText =
  "display:flex;align-items:center;gap:9px;font-size:12px;margin:12px 0";
aiControl.innerHTML =
  '<input id="experiment-ai" type="checkbox"> Compare rules vs. AI-assisted decisions (requires configured key; uses API budget)';
$("#run-experiment").before(aiControl);
$("#run-experiment").onclick = () => {
  playing = false;
  schedule();
  action("experiment", {
    seeds: clamp(num($("#experiment-seeds").value, 3), 1, 10),
    horizon: clamp(num($("#experiment-horizon").value, 30), 14, 365),
    scenario: $("#experiment-scenario").value,
    mode: $("#experiment-ai").checked ? "ai" : "rules",
  });
  $("#experiment-results").innerHTML =
    '<p class="hint">Running paired worlds. This may take a moment…</p>';
};
const aiPanel = document.createElement("div");
aiPanel.className = "side-box";
aiPanel.innerHTML =
  '<div class="eyebrow">Event cognition</div><p id="ai-status" class="hint">Rules engine active. Configure optional AI in Settings.</p><button id="reflect" disabled>Reflect on an event</button>';
$(".side-footer").before(aiPanel);
$("#reflect").onclick = () => action("reflect");
window.addEventListener("message", (e) => {
  if (e.source !== window.parent || e.data?.type !== "streamlit:render") return;
  const ai = e.data.args?.ai || {};
  $("#reflect").disabled = !ai.enabled || busy;
  $("#mode-badge").textContent = ai.enabled
    ? "RULES + OPTIONAL AI · " + num(ai.calls) + " CALLS"
    : "RULES-BASED AGENTS · AI OFF";
  $("#ai-status").textContent = ai.enabled
    ? `${ai.status || "AI ready"} · ${num(ai.calls)} / ${num(ai.max_calls)} calls used. Reflection uses API budget.`
    : "Citizens use programmed rules. Real AI reflections require your key in Settings; Play never calls AI.";
  $("#experiment-ai").disabled = !ai.enabled;
  if (!ai.enabled) $("#experiment-ai").checked = false;
});
// The state-driven voxel renderer owns canvas animation and interaction.
const canvas = $("#world-canvas"),
  scene = $("#scene");
const worldView = new NewHavenWorld(canvas, {
  onSelect(selection) {
    selected = selection;
    renderInspector();
  },
});
function resize() {
  worldView.resize();
}
$("#zoom-in").onclick = () => worldView.zoom(1.2);
$("#zoom-out").onclick = () => worldView.zoom(1 / 1.2);
$("#recenter").onclick = () => worldView.recenter();

function renderIntervention() {
  const option = (S.interventions || []).find(
    (o) => o.id === $("#intervention").value,
  );
  if (!option) return;
  const explanations = {
    storm:
      "Destroys 28% of stored food, damages buildings and disrupts trade for 14 days. Emergency response costs up to " +
      money(num(S.population) * 1.2) +
      "; repairs cost more.",
    aid: "External aid: two days of food with council-paid transport. Emergency only; 30-day cooldown. No money grant.",
    festival:
      "30-day cooldown. Smaller mood benefits for already-happy citizens.",
    education: "Higher wages; rising investment costs and a 30-day cooldown.",
    automation:
      "Diminishing harvest gains; rising investment costs and a 30-day cooldown.",
    tax: "Switches flat income tax between 8% and 15%; 7-day cooldown.",
    market: "Toggles the food price cap; 7-day cooldown.",
  };
  $("#intervention-detail").textContent =
    (option.id === "storm"
      ? ""
      : "Council cost " + money(option.cost) + " · ") +
    option.description +
    ". " +
    (explanations[option.id] || "");
  $("#intervene").disabled = busy || !option.available;
}
function renderConsequences() {
  const l = S.ledger || {},
    resource = S.resources || {};
  const row = (label, value, type = "") =>
    '<div class="ledger-row ' +
    type +
    '"><span>' +
    esc(label) +
    "</span><strong>" +
    esc(value) +
    "</strong></div>";
  $("#world-alerts").innerHTML = (S.active_effects || [])
    .map(
      (e) =>
        '<div class="crisis"><strong>⚠ ' +
        esc(e.label) +
        "</strong><span>" +
        fmt(e.days_remaining) +
        " days of disruption remaining · Inspect buildings for lasting damage.</span></div>",
    )
    .join("");
  $("#daily-ledger").innerHTML =
    '<div class="ledger-group"><div class="eyebrow">Food · meals</div>' +
    row("Opening reserves", fmt(l.food_opening)) +
    row("Harvest & foraging", "+" + fmt(l.food_produced), "positive") +
    row("Relief imported", "+" + fmt(l.food_imported), "positive") +
    row("Eaten", "−" + fmt(l.food_consumed)) +
    row("Lost / spoiled", "−" + fmt(l.food_lost), "negative") +
    row("Closing reserves", fmt(l.food_closing ?? S.food)) +
    '</div><div class="ledger-group"><div class="eyebrow">Money · whole economy</div>' +
    row("Opening money", money(l.money_opening)) +
    row("External trade", "+" + money(l.trade_income), "positive") +
    row("God-mode grant", "+" + money(l.god_money_added), "positive") +
    row("God-mode removal", "−" + money(l.god_money_removed), "negative") +
    row("Upkeep / policies", "−" + money(l.maintenance_cost)) +
    row(
      "Repairs / emergency response",
      "−" + money(l.repair_cost),
      "negative",
    ) +
    row("Relief transport", "−" + money(l.relief_cost)) +
    row("Closing money", money(l.money_closing)) +
    '<p class="hint">Taxes, wages and purchases transfer existing money. Materials: ' +
    fmt(resource.wood) +
    " wood / " +
    fmt(resource.stone) +
    " stone.</p></div>";
  $("#places").innerHTML = (S.buildings || [])
    .map(
      (b) =>
        '<button class="place ' +
        (num(b.condition, 100) < 95 ? "damaged" : "") +
        '" data-place="' +
        esc(b.id) +
        '"><span>' +
        esc(b.name) +
        "</span><small>" +
        fmt(b.condition ?? 100) +
        "%</small></button>",
    )
    .join("");
  $$("[data-place]").forEach(
    (b) =>
      (b.onclick = () => {
        selected = { type: "building", id: b.dataset.place };
        renderInspector();
      }),
  );
  const decisions = S.decision_log || [];
  $("#decision-summary").innerHTML =
    "<p>Programmed responses are <strong>RULES</strong>. Only a completed language-model call is <strong>AI</strong>. " +
    fmt((S.pending_decisions || []).length) +
    " events await optional reflection.</p>";
  $("#decisions").innerHTML =
    decisions
      .slice(-5)
      .reverse()
      .map(
        (d) =>
          '<div class="decision"><span class="tag">' +
          (d.source === "rules" ? "RULES" : "AI") +
          "</span><strong>" +
          esc(citizen(d.citizen_id)?.name || "Citizen") +
          "</strong><p>" +
          esc(d.reason || d.action) +
          "</p>" +
          (d.effect
            ? "<p><strong>Actual effect:</strong> " + esc(d.effect) + "</p>"
            : "") +
          '<span class="hint">Day ' +
          fmt(d.day) +
          " · " +
          esc(String(d.action || "").replaceAll("_", " ")) +
          "</span></div>",
      )
      .join("") ||
    "<p>No recorded decisions yet. Advance time or introduce a crisis.</p>";
  renderIntervention();
}

let lastFrameHeight = 0;
function height() {
  requestAnimationFrame(() => {
    const next = Math.min(
      15000,
      Math.max(950, Math.ceil($(".shell").getBoundingClientRect().height) + 15),
    );
    if (next !== lastFrameHeight) {
      lastFrameHeight = next;
      post("streamlit:setFrameHeight", { height: next });
    }
  });
}
window.addEventListener("message", (e) => {
  if (e.source !== window.parent || e.data?.type !== "streamlit:render") return;
  const args = e.data.args || {},
    acknowledged = pendingId !== null && args.ack === pendingId;
  const completedAction = acknowledged ? pendingAction : null;
  if (args.state) {
    const replaced = acknowledged && ["reset", "load"].includes(pendingAction);
    oldPositions = replaced
      ? new Map()
      : new Map(
          living().map((c) => [String(c.id), { x: num(c.x), y: num(c.y) }]),
        );
    S = args.state;
    transitionStart = performance.now();
    if (!receivedState || replaced) {
      $("#population").value = S.population ?? 100;
      $("#seed").value = S.seed ?? 7;
      receivedState = true;
    }
    if (replaced) {
      selected = null;
      worldView.recenter();
    }
    worldView.setState(S);
    renderConsequences();
    renderMetrics();
    renderInspector();
    renderPeople();
    renderEvents();
    renderEconomy();
  }
  if (acknowledged) {
    busy = false;
    pendingId = null;
    pendingAction = null;
  }
  $("#error").textContent = args.error || "";
  $("#error").style.display = args.error ? "block" : "none";
  if (args.error) {
    playing = false;
    toast(args.error);
  }
  if (args.experiment) renderExperiment(args.experiment);
  else if (acknowledged && !args.error) $("#experiment-results").innerHTML = "";
  if (args.save_data && args.save_id && args.save_id !== lastSave) {
    lastSave = args.save_id;
    const blob = new Blob(
        [
          typeof args.save_data === "string"
            ? args.save_data
            : JSON.stringify(args.save_data),
        ],
        { type: "application/json" },
      ),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = "new-haven-day-" + num(S.day) + ".json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("World saved. Its story is yours to keep.");
  }
  renderFeatureState(args, completedAction);
  updateControls();
  schedule();
  resize();
  height();
  if (completedAction === "configure_ai") action("settings_ack");
});
// Every outgoing action has an explicit acknowledgement. Unrelated rerenders do not unlock controls.
action = function (actionName, data = {}) {
  if (busy) return;
  pendingId = Date.now() + "-" + ++sequence;
  pendingAction = actionName;
  busy = true;
  if (
    [
      "reset",
      "load",
      "god_interpret",
      "god_apply",
      "configure_ai",
      "forget_ai",
    ].includes(actionName)
  ) {
    playing = false;
    clearTimeout(timer);
  }
  updateControls();
  post("streamlit:setComponentValue", {
    value: { id: pendingId, action: actionName, ...data },
  });
};
$("#top-nav").append(document.querySelector("nav"));
$(".topbar").append($("#menu"));
$("#intervention").onchange = renderIntervention;
new ResizeObserver(() => {
  resize();
  height();
}).observe(scene);
window.addEventListener("resize", height);
initializeFeatures();
renderMetrics();
renderInspector();
renderPeople();
renderEvents();
renderEconomy();
resize();

post("streamlit:componentReady", { apiVersion: 1 });
height();

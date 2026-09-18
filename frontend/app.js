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
}
function setTab(tab) {
  activeTab = tab;
  $$(".section").forEach((el) => el.classList.toggle("active", el.id === tab));
  $$("nav button").forEach((el) =>
    el.classList.toggle("active", el.dataset.tab === tab),
  );
  $("#sidebar").classList.remove("open");
  const names = {
    world: [
      "A little world. A life of its own.",
      "Every citizen has a story. See what happens next.",
    ],
    citizens: [
      "The people of New Haven",
      "Individual lives. Shared possibilities.",
    ],
    economy: [
      "What keeps a world going",
      "Follow resources, livelihoods, and the balance between them.",
    ],
    chronicle: [
      "A history, still being written",
      "The moments that change a place and its people.",
    ],
    experiments: [
      "Explore another possibility",
      "Same beginning. Different choices. What changes?",
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
    horizon: clamp(num($("#experiment-horizon").value, 90), 30, 365),
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
      `<div class="eyebrow">Around the settlement</div><div class="avatar" style="margin-top:15px">${b.kind === "farm" ? "🌾" : b.kind === "mine" ? "⛰" : "⌂"}</div><h2>${esc(b.name || b.kind)}</h2><p>${esc(b.kind)}</p><hr class="separator"><p class="muted">A part of the town’s shared life. Citizens travel between homes, work, and public spaces.</p>${biz ? `<div class="goal">${(biz.workers || []).length} workers · Cash ${money(biz.cash)}<br>Daily profit ${money(biz.profit)}</div>` : ""}<button id="clear-selection">Back to town overview</button>`;
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
    `<div style="display:flex;justify-content:space-between"><div class="eyebrow">Resident journal</div><button class="link" id="clear-selection" aria-label="Close resident inspector">✕</button></div><div class="avatar" style="margin-top:14px">${num(c.age) < 18 ? "🧒" : num(c.age) > 65 ? "🧓" : "🧑"}</div><h2>${esc(c.name)}</h2><p class="muted">${esc(c.job || "Seeking work")} · Age ${Math.floor(num(c.age))}</p><p style="font-size:12px;margin-top:10px">${esc(c.activity || "Taking in the town")}</p><div class="goal"><span class="eyebrow">Working towards</span><br>${esc(c.goal || "A good life in New Haven")}</div>${need("Happiness", c.happiness)}${need("Health", c.health)}${need("Energy", c.energy)}${need("Food security", 100 - num(c.hunger))}<p class="muted">Savings <strong>${money(c.wealth)}</strong></p><hr class="separator"><div class="eyebrow">Personality</div><p class="muted">${
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
    ["Food stores", fmt(S.food), "Price £" + num(S.food_price).toFixed(2)],
    ["Shared treasury", money(S.treasury), "Resources for tomorrow"],
    ["Happiness", fmt(S.happiness) + "%", "The mood of the town"],
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
    horizon: clamp(num($("#experiment-horizon").value, 90), 30, 365),
    scenario: $("#experiment-scenario").value,
    mode: $("#experiment-ai").checked ? "ai" : "rules",
  });
  $("#experiment-results").innerHTML =
    '<p class="hint">Running paired worlds. This may take a moment…</p>';
};
const aiPanel = document.createElement("div");
aiPanel.className = "side-box";
aiPanel.innerHTML =
  '<div class="eyebrow">Event cognition</div><p id="ai-status" class="hint">Rules engine active. Optional AI setup is below the app.</p><button id="reflect" disabled>Reflect on an event</button>';
$(".side-footer").before(aiPanel);
$("#reflect").onclick = () => action("reflect");
window.addEventListener("message", (e) => {
  if (e.source !== window.parent || e.data?.type !== "streamlit:render") return;
  const ai = e.data.args?.ai || {};
  $("#reflect").disabled = !ai.enabled;
  $("#ai-status").textContent = ai.enabled
    ? `${ai.status || "AI ready"} · ${num(ai.calls)} / ${num(ai.max_calls)} calls used. Reflection uses API budget.`
    : "Rules engine active. Enable optional AI using the setup panel below the app.";
  $("#experiment-ai").disabled = !ai.enabled;
  if (!ai.enabled) $("#experiment-ai").checked = false;
});
// Canvas renderer: all scenery is generated locally from the actual world snapshot.
const canvas = $("#world-canvas"),
  ctx = canvas.getContext("2d"),
  scene = $("#scene");
let width = 700,
  heightPx = 490,
  zoom = 1,
  panX = 0,
  panY = 0,
  hits = [],
  drag = null,
  raf = 0;
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
function resize() {
  width = scene.clientWidth || 700;
  heightPx = scene.clientHeight || 490;
  const dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = width * dpr;
  canvas.height = heightPx * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
function worldSize() {
  return {
    w: num(S.width || S.world_width, 24),
    h: num(S.height || S.world_height, 20),
  };
}
function scale() {
  const { w, h } = worldSize();
  return Math.min(width / (w + h + 3), heightPx / (0.5 * (w + h) + 7)) * zoom;
}
function iso(x, y, z = 0) {
  const { w, h } = worldSize(),
    s = scale();
  return [
    width / 2 + (x - y - (w - h) / 2) * s + panX,
    heightPx / 2 + ((x + y - (w + h) / 2) * 0.5 - z) * s + panY + 20,
  ];
}
function poly(points, fill, stroke) {
  ctx.beginPath();
  points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }
}
function tile(x, y, color) {
  poly([iso(x, y), iso(x + 1, y), iso(x + 1, y + 1), iso(x, y + 1)], color);
}
function block(x, y, w, d, h, colors) {
  poly(
    [iso(x, y, h), iso(x + w, y, h), iso(x + w, y + d, h), iso(x, y + d, h)],
    colors[0],
  );
  poly(
    [iso(x, y + d, h), iso(x + w, y + d, h), iso(x + w, y + d), iso(x, y + d)],
    colors[1],
  );
  poly(
    [iso(x + w, y, h), iso(x + w, y + d, h), iso(x + w, y + d), iso(x + w, y)],
    colors[2],
  );
}
function tree(x, y, seed) {
  block(x + 0.43, y + 0.43, 0.12, 0.12, 0.55, [
    "#87754d",
    "#75603d",
    "#665735",
  ]);
  const h = 0.8 + (seed % 3) * 0.13;
  for (let i = 0; i < 3; i++) {
    const z = 0.5 + i * 0.33,
      r = 0.45 - i * 0.1;
    poly(
      [
        iso(x + 0.5 - r, y + 0.5 + r, z),
        iso(x + 0.5, y + 0.5, z + h * 0.7),
        iso(x + 0.5 + r, y + 0.5 + r, z),
      ],
      "#56764c",
    );
    poly(
      [
        iso(x + 0.5 + r, y + 0.5 - r, z),
        iso(x + 0.5, y + 0.5, z + h * 0.7),
        iso(x + 0.5 + r, y + 0.5 + r, z),
      ],
      "#3f6344",
    );
  }
}
function building(b) {
  const x = num(b.x),
    y = num(b.y),
    kind = String(b.kind || "home").toLowerCase(),
    s = scale();
  if (kind.includes("farm")) {
    tile(x, y, "#b29c50");
    for (let i = 0; i < 5; i++) {
      const a = iso(x + 0.12 + i * 0.17, y + 0.12, 0.1),
        d = iso(x + 0.12 + i * 0.17, y + 0.9, 0.1);
      ctx.strokeStyle = "#e3c862";
      ctx.lineWidth = Math.max(1, s * 0.08);
      ctx.beginPath();
      ctx.moveTo(...a);
      ctx.lineTo(...d);
      ctx.stroke();
    }
  } else if (kind.includes("mine")) {
    block(x + 0.1, y + 0.1, 0.8, 0.8, 0.6, ["#929a91", "#667a73", "#7c8980"]);
    block(x + 0.3, y + 0.75, 0.38, 0.1, 0.35, [
      "#665c4d",
      "#344844",
      "#4d5b53",
    ]);
  } else {
    const tall =
        kind.includes("council") ||
        kind.includes("hall") ||
        kind.includes("school"),
      h = tall ? 1.35 : 0.85,
      roof = kind.includes("market")
        ? "#ae8050"
        : kind.includes("work")
          ? "#688e92"
          : kind.includes("school")
            ? "#79815f"
            : "#b77957";
    block(x + 0.08, y + 0.08, 0.85, 0.85, h, ["#ece0bc", "#d4c6a1", "#eee3c4"]);
    const a = iso(x + 0.01, y + 0.01, h),
      b1 = iso(x + 1, y + 0.01, h),
      c = iso(x + 1, y + 1, h),
      d = iso(x + 0.01, y + 1, h),
      r1 = iso(x + 0.5, y + 0.01, h + 0.47),
      r2 = iso(x + 0.5, y + 1, h + 0.47);
    poly([a, r1, r2, d], roof);
    poly([r1, b1, c, r2], kind.includes("work") ? "#4c7277" : "#925a44");
    block(x + 0.36, y + 0.94, 0.22, 0.025, 0.4, [
      "#776548",
      "#766546",
      "#675b44",
    ]);
    const win = iso(x + 0.94, y + 0.35, 0.54);
    ctx.fillStyle = "#4f807e";
    ctx.fillRect(win[0] - s * 0.07, win[1] - s * 0.12, s * 0.13, s * 0.2);
    if (tall) {
      block(x + 0.4, y + 0.3, 0.25, 0.25, h + 0.5, [
        "#dfcead",
        "#b9a483",
        "#cec09c",
      ]);
    }
  }
  const p = iso(x + 0.5, y + 0.5, 0.6);
  hits.push({
    x: p[0],
    y: p[1],
    radius: Math.max(12, s),
    type: "building",
    id: b.id,
    label: b.name || b.kind,
  });
}
function draw(now) {
  ctx.clearRect(0, 0, width, heightPx);
  hits = [];
  const { w, h } = worldSize(),
    terrain = new Map((S.terrain || []).map((t) => [t.x + "," + t.y, t.kind])),
    s = scale();
  poly(
    [iso(0, 0, -0.35), iso(w, 0, -0.35), iso(w, h, -0.35), iso(0, h, -0.35)],
    "#91ac81",
  );
  for (let total = 0; total < w + h; total++)
    for (let x = 0; x < w; x++) {
      const y = total - x;
      if (y < 0 || y >= h) continue;
      const kind =
        terrain.get(x + "," + y) ||
        (x === 3 || x === 4 ? "water" : y === 9 || x === 12 ? "road" : "grass");
      let color =
        kind === "water" || kind === "river"
          ? "#83bac0"
          : kind === "road"
            ? "#d9cda4"
            : kind === "farm"
              ? "#b8aa63"
              : kind === "sand"
                ? "#d7cba0"
                : ["#a9c28e", "#a5bf88", "#abc590", "#a2bd85"][
                    (x * 7 + y * 11) % 4
                  ];
      tile(x, y, color);
      if ((kind === "water" || kind === "river") && (x + y) % 3 === 0) {
        const p = iso(x + 0.25, y + 0.5);
        ctx.strokeStyle = "#b5d9d1";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p[0], p[1]);
        ctx.lineTo(p[0] + s * 0.35, p[1] + s * 0.12);
        ctx.stroke();
      }
    }
  const objects = [];
  for (const t of S.terrain || [])
    if (t.kind === "forest" || t.kind === "tree")
      objects.push({
        depth: num(t.x) + num(t.y),
        draw: () => tree(num(t.x), num(t.y), num(t.x) * 3 + num(t.y)),
      });
  if (!(S.terrain || []).length) {
    for (let y = 1; y < h; y += 2)
      for (let x = 1; x < w; x += 2)
        if (x > 5 && (x * 7 + y * 13) % 11 < 3)
          objects.push({ depth: x + y, draw: () => tree(x, y, x + y) });
  }
  (S.buildings || []).forEach((b) =>
    objects.push({ depth: num(b.x) + num(b.y) + 1, draw: () => building(b) }),
  );
  living().forEach((c) => {
    const previous = oldPositions.get(String(c.id)),
      t = reduced ? 1 : clamp((now - transitionStart) / 900, 0, 1),
      x = previous ? previous.x + (num(c.x) - previous.x) * t : num(c.x),
      y = previous ? previous.y + (num(c.y) - previous.y) * t : num(c.y),
      j = ((num(c.id) * 0.618) % 1) - 0.5,
      k = ((num(c.id) * 0.317) % 1) - 0.5;
    objects.push({
      depth: x + y + 1.2,
      draw: () => {
        const [px, py] = iso(x + 0.5 + j * 0.45, y + 0.5 + k * 0.45),
          r = clamp(s * 0.12, 2.1, 5.5),
          bob = !reduced && t < 1 ? Math.sin(now * 0.02 + num(c.id)) * 1 : 0;
        ctx.fillStyle = "#254b3e30";
        ctx.beginPath();
        ctx.ellipse(px, py + 2, r * 1.3, r * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#486252";
        ctx.lineWidth = Math.max(1, r * 0.4);
        ctx.beginPath();
        ctx.moveTo(px - r * 0.4, py);
        ctx.lineTo(px - r * 0.4, py - r);
        ctx.moveTo(px + r * 0.4, py);
        ctx.lineTo(px + r * 0.4, py - r);
        ctx.stroke();
        ctx.fillStyle =
          num(c.happiness) > 65
            ? "#e9be58"
            : num(c.happiness) < 40
              ? "#d47b58"
              : "#619689";
        ctx.fillRect(px - r * 0.7, py - r * 2 + bob, r * 1.4, r * 1.7);
        ctx.fillStyle = ["#deb998", "#c99d78", "#a87959"][
          Math.abs(Math.floor(num(c.id))) % 3
        ];
        ctx.beginPath();
        ctx.arc(px, py - r * 2.5 + bob, r * 0.7, 0, Math.PI * 2);
        ctx.fill();
        if (
          selected?.type === "citizen" &&
          String(selected.id) === String(c.id)
        ) {
          ctx.strokeStyle = "#183f33";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.ellipse(px, py + 3, r * 2.4, r * 1.2, 0, 0, Math.PI * 2);
          ctx.stroke();
          ctx.fillStyle = "#183f33";
          ctx.beginPath();
          ctx.moveTo(px, py - r * 4);
          ctx.lineTo(px - 3, py - r * 5);
          ctx.lineTo(px + 3, py - r * 5);
          ctx.fill();
        }
        hits.push({
          x: px,
          y: py - r,
          radius: Math.max(8, r * 2),
          type: "citizen",
          id: c.id,
          label: c.name + " · " + (c.activity || c.job || "Resident"),
        });
      },
    });
  });
  objects.sort((a, b) => a.depth - b.depth).forEach((o) => o.draw());
  if (/storm|rain/i.test(S.weather || "")) {
    ctx.fillStyle = "#597d9620";
    ctx.fillRect(0, 0, width, heightPx);
  }
  raf = requestAnimationFrame(draw);
}
function hit(e) {
  const rect = canvas.getBoundingClientRect(),
    x = e.clientX - rect.left,
    y = e.clientY - rect.top;
  return hits
    .filter((h) => Math.hypot(x - h.x, y - h.y) < h.radius)
    .sort(
      (a, b) =>
        (a.type === "citizen" ? -1 : 1) - (b.type === "citizen" ? -1 : 1) ||
        Math.hypot(x - a.x, y - a.y) - Math.hypot(x - b.x, y - b.y),
    )[0];
}
canvas.onpointerdown = (e) => {
  drag = { x: e.clientX, y: e.clientY, px: panX, py: panY, moved: false };
  canvas.setPointerCapture(e.pointerId);
};
canvas.onpointermove = (e) => {
  if (drag) {
    const dx = e.clientX - drag.x,
      dy = e.clientY - drag.y;
    drag.moved = drag.moved || Math.abs(dx) + Math.abs(dy) > 5;
    panX = drag.px + dx;
    panY = drag.py + dy;
    $("#tooltip").style.display = "none";
  } else {
    const h = hit(e),
      tip = $("#tooltip");
    if (h) {
      tip.textContent = h.label;
      tip.style.display = "block";
      tip.style.left = clamp(h.x + 12, 8, width - 190) + "px";
      tip.style.top = clamp(h.y - 30, 8, heightPx - 40) + "px";
    } else tip.style.display = "none";
  }
};
canvas.onpointerup = (e) => {
  if (drag && !drag.moved) {
    const h = hit(e);
    if (h) {
      selected = { type: h.type, id: h.id };
      renderInspector();
    }
  }
  drag = null;
};
canvas.onpointercancel = () => (drag = null);
canvas.onpointerleave = () => ($("#tooltip").style.display = "none");
canvas.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    zoom = clamp(zoom * (e.deltaY < 0 ? 1.08 : 0.92), 0.55, 3);
  },
  { passive: false },
);
$("#zoom-in").onclick = () => (zoom = clamp(zoom * 1.2, 0.55, 3));
$("#zoom-out").onclick = () => (zoom = clamp(zoom / 1.2, 0.55, 3));
$("#recenter").onclick = () => {
  zoom = 1;
  panX = panY = 0;
};
canvas.onkeydown = (e) => {
  if (
    [
      "+",
      "=",
      "-",
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "ArrowDown",
      "Home",
    ].includes(e.key)
  )
    e.preventDefault();
  if (e.key === "+" || e.key === "=") zoom = clamp(zoom * 1.15, 0.55, 3);
  if (e.key === "-") zoom = clamp(zoom / 1.15, 0.55, 3);
  if (e.key === "ArrowLeft") panX += 25;
  if (e.key === "ArrowRight") panX -= 25;
  if (e.key === "ArrowUp") panY += 25;
  if (e.key === "ArrowDown") panY -= 25;
  if (e.key === "Home") {
    panX = panY = 0;
    zoom = 1;
  }
};
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
      zoom = 1;
      panX = panY = 0;
    }
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
  updateControls();
  schedule();
  resize();
  height();
});
// Every outgoing action has an explicit acknowledgement. Unrelated rerenders do not unlock controls.
action = function (actionName, data = {}) {
  if (busy) return;
  pendingId = Date.now() + "-" + ++sequence;
  pendingAction = actionName;
  busy = true;
  if (["reset", "load"].includes(actionName)) {
    playing = false;
    clearTimeout(timer);
  }
  updateControls();
  post("streamlit:setComponentValue", {
    value: { id: pendingId, action: actionName, ...data },
  });
};
new ResizeObserver(() => {
  resize();
  height();
}).observe(scene);
window.addEventListener("resize", height);
renderMetrics();
renderInspector();
renderPeople();
renderEvents();
renderEconomy();
resize();
requestAnimationFrame(draw);
post("streamlit:componentReady", { apiVersion: 1 });
height();

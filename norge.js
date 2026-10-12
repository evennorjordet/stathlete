// Stathlete Norge — guess the mystery Norwegian athlete.
// Loads data/athletes_mode2.json (built by scraper/mode2/scrape_minstat.py).
// Each guess renders as its own card, like the World mode.

const TOP_SHOWN = 5;

function groupFromEvent(ev) {
  const e = ev.toLowerCase();
  if (/^\d+ kamp/.test(e)) return "Mangekamp";
  if (e.includes("hekk") || e.includes("hinder")) return "Hekk";
  if (/^(høyde|stav|lengde|tresteg)/.test(e)) return "Hopp";
  if (/^(kule|diskos|spyd|slegge)/.test(e)) return "Kast";
  const m = e.match(/^(\d+) meter/);
  if (m) return parseInt(m[1], 10) <= 400 ? "Sprint" : "Mellom-/langdistanse";
  return "Annet";
}

const pbKey = (season, pb) => season + "|" + pb.event;

// "300 meter hekk (84,0cm)" and "300 meter hekk (76,2cm)" are the same discipline, as are
// "Kule 4,0kg" / "Kule 5,0kg" and "Lengde (Sone 0,5m)" / "Lengde": strip height/weight/zone.
function baseEvent(ev) {
  return ev.replace(/\s*\([^)]*\)/g, "").replace(/\s+\d+(,\d+)?\s*(kg|gram)$/i, "").trim();
}

const GENDER_LABEL = { Gutter: "Mann", Jenter: "Kvinne" };

function buildAthlete(raw) {
  const pbs = [];
  for (const season of ["outdoor", "indoor"]) {
    for (const p of raw.personal_bests[season]) pbs.push({ ...p, season, key: pbKey(season, p) });
  }
  return {
    id: raw.id, name: raw.name, club: raw.club, region: raw.region,
    gender: GENDER_LABEL[raw.gender] || raw.gender,
    born: raw.born, medals: raw.um_medals.total, score: raw.score || 0,
    results: raw.result_count || 0,
    mainEvent: raw.main_event || "",
    group: raw.main_event ? groupFromEvent(raw.main_event) : "Annet",
    pbs, // site order: outdoor first, then indoor, events in minfriidrettsstatistikk's order
    featured: pbs.filter(p => p.featured).sort((a, b) => b.points - a.points),
  };
}

let athletes = [], target = null, guessedNames = new Set();

const els = {
  guesses: document.getElementById("guesses"), form: document.getElementById("guess-form"),
  input: document.getElementById("guess-input"), submit: document.getElementById("guess-submit"),
  error: document.getElementById("error"), status: document.getElementById("status"),
  reset: document.getElementById("reset"),
};

function pickTarget() {
  const pool = athletes.filter(a => !target || a.id !== target.id);
  target = pool[Math.floor(Math.random() * pool.length)];
}

function arrow(dir) {
  const s = document.createElement("span");
  s.className = "arrow"; s.setAttribute("aria-hidden", "true");
  s.textContent = dir === "up" ? "\u2191" : dir === "down" ? "\u2193" : "=";
  return s;
}

function chip(label, value, state) {
  const c = document.createElement("span");
  c.className = "chip" + (state ? " " + state : "");
  const l = document.createElement("span");
  l.className = "chip-label"; l.textContent = label;
  c.appendChild(l); c.appendChild(document.createTextNode(value));
  return c;
}

function numChip(label, g, t) {
  if (g === t) return chip(label, String(g), "match");
  const c = chip(label, String(g), null);
  c.appendChild(arrow(t > g ? "up" : "down"));
  return c;
}

// PB rows carry no colours. The arrow (if any) compares this mark with the target's PB in
// the same event and season: up = target is better, down = target is worse, "=" = identical.
function pbCompare(pb) {
  const tp = target.pbs.find(p => p.key === pb.key);
  if (!tp) return null;
  if (tp.value === pb.value) return "equal";
  return (pb.lower_is_better ? tp.value < pb.value : tp.value > pb.value) ? "up" : "down";
}

function pbRow(pb) {
  const dir = pbCompare(pb);
  const row = document.createElement("div");
  row.className = "ev-row";
  const name = document.createElement("span");
  name.className = "ev-name"; name.textContent = pb.event;
  const val = document.createElement("span");
  val.className = "ev-val"; val.textContent = pb.display;
  if (dir) val.appendChild(arrow(dir));
  row.appendChild(name); row.appendChild(val);
  return row;
}

function renderPbs(wrap, g, showAll) {
  wrap.innerHTML = "";
  if (!showAll) {
    g.featured.forEach(pb => wrap.appendChild(pbRow(pb)));
    return;
  }
  [["outdoor", "Utendørs"], ["indoor", "Innendørs"]].forEach(([season, title]) => {
    const list = g.pbs.filter(p => p.season === season);
    if (!list.length) return;
    const h = document.createElement("p");
    h.className = "pb-section-title"; h.textContent = title;
    wrap.appendChild(h);
    list.forEach(pb => wrap.appendChild(pbRow(pb)));
  });
}

function renderGuessCard(g) {
  const placeholder = els.guesses.querySelector(".empty");
  if (placeholder) placeholder.remove();

  const card = document.createElement("div");
  card.className = "guess-card";
  const name = document.createElement("span");
  name.className = "gc-name"; name.textContent = g.name;
  card.appendChild(name);

  const chips = document.createElement("div");
  chips.className = "gc-chips";
  chips.appendChild(chip("Kjønn", g.gender, g.gender === target.gender ? "match" : null));
  chips.appendChild(chip("Klubb", g.club, g.club === target.club ? "match" : null));
  if (g.region) chips.appendChild(chip("Krets", g.region, g.region === target.region ? "match" : null));
  chips.appendChild(numChip("Født", g.born, target.born));
  chips.appendChild(numChip("UM-medaljer", g.medals, target.medals));
  chips.appendChild(numChip("Poeng", g.score, target.score));
  chips.appendChild(numChip("Resultater", g.results, target.results));
  if (g.mainEvent) {
    const same = baseEvent(g.mainEvent) === baseEvent(target.mainEvent);
    const sameType = groupFromEvent(g.mainEvent) === target.group;
    chips.appendChild(chip("Hovedøvelse", g.mainEvent, same ? "match" : sameType ? "partial" : null));
  }
  card.appendChild(chips);

  const heading = document.createElement("p");
  heading.className = "gc-pbs-heading";
  heading.textContent = `Personlige rekorder (${g.pbs.length})`;
  card.appendChild(heading);

  const wrap = document.createElement("div");
  renderPbs(wrap, g, false);
  card.appendChild(wrap);

  if (g.pbs.length > g.featured.length) {
    let all = false;
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "show-more";
    const label = () => (btn.textContent = all ? "Vis færre" : `Vis alle (${g.pbs.length})`);
    label();
    btn.addEventListener("click", () => { all = !all; renderPbs(wrap, g, all); label(); });
    card.appendChild(btn);
  }
  els.guesses.prepend(card);
}

function endGame(won) {
  els.status.textContent = won ? `Riktig — det var ${target.name}.` : `Tom for utøvere — det var ${target.name}.`;
  els.input.disabled = true;
  els.submit.disabled = true;
  els.reset.hidden = false;
}

function showError(msg) { els.error.textContent = msg; els.error.hidden = false; }

function submitGuess(ev) {
  ev.preventDefault();
  els.error.hidden = true;
  const val = els.input.value.trim();
  if (!val) return showError("Skriv inn et utøvernavn først.");
  const found = athletes.find(a => a.name.toLowerCase() === val.toLowerCase());
  if (!found) return showError("Velg et navn fra listen.");
  if (guessedNames.has(found.id)) return showError("Du har allerede gjettet den utøveren.");
  guessedNames.add(found.id);
  renderGuessCard(found);
  els.input.value = "";
  if (found.id === target.id) endGame(true);
  else if (guessedNames.size >= athletes.length) endGame(false);
}

function newGame() {
  pickTarget();
  guessedNames = new Set();
  els.guesses.innerHTML = '<p class="empty">Gjett for å se hvor nær du er.</p>';
  els.status.textContent = ""; els.error.hidden = true; els.reset.hidden = true;
  els.input.disabled = false; els.submit.disabled = false; els.input.value = "";
}

async function init() {
  const res = await fetch("data/athletes_mode2.json");
  const data = await res.json();
  athletes = data.athletes.map(buildAthlete);
  createCombobox({
    input: els.input, toggle: document.getElementById("combo-toggle"),
    list: document.getElementById("athlete-listbox"),
    getOptions: () => athletes.map(a => a.name),
    isUsed: name => guessedNames.has(athletes.find(a => a.name === name)?.id),
    emptyText: "Ingen treff",
  });
  els.form.addEventListener("submit", submitGuess);
  els.reset.addEventListener("click", newGame);
  newGame();
}

init();

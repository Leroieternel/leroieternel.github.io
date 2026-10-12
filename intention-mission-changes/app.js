"use strict";
const $ = id => document.getElementById(id);
const fmt = n => Number(n).toLocaleString("en-US");
const esc = text => String(text ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const names = {original:"Original · 8,897", historical:"Regrouped · 10,612", latest:"Latest · 10,373"};
const store = "intention-mission-change-review-20261012";
let catalog, filtered = [], current = null, selection = 0, pendingFrame = 0;
const cache = new Map();
let notes = {};
try { notes = JSON.parse(localStorage.getItem(store) || "{}"); } catch (_) { notes = {}; }

function fail(error) { $("error").hidden = false; $("error").textContent = error.message || String(error); }
async function fetchJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Unable to load ${path}: HTTP ${response.status}`);
  return response.json();
}
function matches(row, scope) {
  if (scope === "increased") return row.delta > 0;
  if (scope === "exact") return row.exact_splits > 0;
  if (scope === "changed-actions") return row.delta > 0 && !row.stable_actions;
  if (scope === "still-increased") return row.delta > 0 && row.missions.latest > row.missions.original;
  if (scope === "remerged") return row.delta > 0 && row.reduced_since;
  if (scope === "decreased") return row.delta < 0;
  if (scope === "structural") return row.structural_change;
  return true;
}
function renderList(preferred) {
  const query = $("search").value.trim().toLowerCase(), scope = $("scope").value;
  const order = new Map(catalog.datasets.map((d, i) => [d.id, i]));
  filtered = catalog.episodes.filter(r => matches(r, scope) &&
    `${r.key} ${r.dataset_label} ${r.instruction} ${r.task}`.toLowerCase().includes(query));
  filtered.sort((a,b) => order.get(a.dataset)-order.get(b.dataset) ||
    ($("sort").value === "increase" ? b.delta-a.delta : 0) || Number(a.episode)-Number(b.episode));
  $("filtered-count").textContent = `${fmt(filtered.length)} matching episodes`;
  const selected = filtered.find(r => r.key === preferred) || filtered.find(r => r.key === current?.key) || filtered[0];
  $("episodes").innerHTML = catalog.datasets.map(ds => {
    const rows = filtered.filter(r => r.dataset === ds.id);
    if (!rows.length) return "";
    return `<details class="dataset" ${selected?.dataset === ds.id ? "open" : ""}><summary>${esc(ds.label)}<span>${fmt(rows.length)}</span></summary>${rows.map(r =>
      `<button class="episode-button ${selected?.key === r.key ? "active" : ""}" data-key="${esc(r.key)}"><b>Episode ${esc(r.episode)}</b><span class="delta">${r.missions.original} → ${r.missions.historical} → ${r.missions.latest}</span><small>${esc(r.instruction)}</small></button>`
    ).join("")}</details>`;
  }).join("");
  $("empty").hidden = !!selected;
  if (!selected) { selection++; current = null; $("detail").hidden = true; $("video").pause(); return; }
  if (selected.key !== current?.key) loadEpisode(selected.key).catch(fail);
  else navigation();
}
function navigation() {
  const index = filtered.findIndex(r => r.key === current?.key);
  $("prev").disabled = index <= 0;
  $("next").disabled = index < 0 || index >= filtered.length-1;
}
async function loadEpisode(key, updateURL=true) {
  const token = ++selection;
  const row = catalog.episodes.find(r => r.key === key);
  if (!row) throw new Error("Episode not found in this comparison.");
  $("error").hidden = true;
  $("video").pause();
  if (!cache.has(row.dataset)) cache.set(row.dataset, fetchJSON(`data/${row.dataset}.json`).catch(error => {cache.delete(row.dataset); throw error;}));
  const rows = await cache.get(row.dataset);
  if (token !== selection) return;
  current = rows.find(r => r.key === key);
  if (!current) throw new Error("Episode data is missing.");
  if (updateURL) history.replaceState(null, "", `?episode=${encodeURIComponent(key)}`);
  document.querySelectorAll(".episode-button").forEach(b => b.classList.toggle("active", b.dataset.key === key));
  const button = [...document.querySelectorAll(".episode-button")].find(b => b.dataset.key === key);
  if (button) button.closest("details").open = true;
  $("detail").hidden = false;
  $("episode-meta").textContent = `${row.dataset_label} · EPISODE ${row.episode} · TASK ${row.task}`;
  $("instruction").textContent = current.instruction;
  const n = current.missions, a = current.actions;
  $("episode-counts").textContent = `Missions ${n.original} → ${n.historical} → ${n.latest} · Actions ${a.original} → ${a.historical} → ${a.latest} · ${current.frames} frames @ ${current.fps} FPS`;
  $("current-editor").href = `https://mcxiangalds.com/intention-current-6600/?episode=${encodeURIComponent(key)}`;
  $("data-warning").hidden = !current.data_flag;
  $("data-warning").textContent = current.data_flag ? `Existing data-quality flag: ${current.data_flag}` : "";
  pendingFrame = 0;
  let url = current.video;
  if (current.dataset === "fastumi_100k" && !url.includes("codec=")) url += `${url.includes("?") ? "&" : "?"}codec=h264-20260902`;
  $("video").src = url;
  $("video-status").textContent = "Loading video…";
  $("frame-input").max = current.frames-1;
  $("frame-input").value = 0;
  renderTracks(); renderMappings(); renderAnnotations(); navigation(); updateFrame();
  $("reasons").innerHTML = `<h4>Recorded at 10,612</h4><p>${esc(current.historical_reason || "No separate rationale was stored.")}</p><h4>Latest recorded rationale</h4><p>${esc(current.latest_reason || "No separate rationale was stored.")}</p>`;
}
function seek(frame) {
  if (!current) return;
  pendingFrame = Math.min(current.frames-1, Math.max(0, Math.round(Number(frame) || 0)));
  if ($("video").readyState >= 1) $("video").currentTime = pendingFrame / current.fps;
  else $("frame-label").textContent = `Frame ${pendingFrame} / ${current.frames-1}`;
}
function updateFrame() {
  if (!current) return;
  const frame = Math.min(current.frames-1, Math.max(0, Math.round($("video").currentTime*current.fps)));
  $("frame-label").textContent = `Frame ${frame} / ${current.frames-1}`;
  if (document.activeElement !== $("frame-input")) $("frame-input").value = frame;
  document.querySelectorAll(".cursor").forEach(cursor => cursor.style.left = `${100*frame/current.frames}%`);
}
function renderTracks() {
  $("timeline").innerHTML = Object.keys(names).map(name => `<div class="timeline-row"><span class="track-name">${names[name]}</span><div class="track ${name}">${current.tracks[name].missions.map((m,i) =>
    `<button data-frame="${m.start}" style="left:${100*m.start/current.frames}%;width:${100*(m.end-m.start+1)/current.frames}%" title="M${i+1}: ${esc(m.label)} · ${m.start}–${m.end}">M${i+1}</button>`
  ).join("")}<span class="cursor"></span></div></div>`).join("") + `<div class="time-axis"><span>Frame 0</span><span>${current.frames-1}</span></div>`;
}
function mini(name, index) {
  const m = current.tracks[name].missions[index];
  return `<button class="mission-mini" data-frame="${m.start}"><b>M${index+1}.</b> ${esc(m.label)}<small>Frames ${m.start}–${m.end} · ${m.actions.length} action${m.actions.length===1?"":"s"}</small></button>`;
}
function renderMappings() {
  $("mapping-note").textContent = current.stable_actions ? "Atomic IDs and frame ranges are unchanged." : "Atomic segmentation changed; mappings use frame overlap.";
  if (!current.splits.length) {
    $("correspondence").innerHTML = `<p class="muted">No original mission maps to multiple regrouped missions. The complete tracks below show any reductions, label changes, or boundary changes.</p>`;
    return;
  }
  $("correspondence").innerHTML = current.splits.map((g,i) => {
    const id = `${current.key}::${g.original}`, note = notes[id] || {};
    const status = {unchanged:"Still separate", fully_remerged:"Merged again", partly_remerged:"Partly merged again"}[g.status];
    const kind = g.exact ? "Confirmed grouping split" : g.method === "frame_overlap" ? "Temporal correspondence" : "Regrouped action membership";
    return `<article class="mapping"><div class="mapping-head"><strong>Original M${g.original+1} → ${g.historical.map(j=>`M${j+1}`).join(" + ")}</strong><span class="badge">${kind}</span><span class="badge ${g.status!=="unchanged"?"green":""}">${status}</span></div>
      <div class="mapping-cols"><div><div class="mapping-label">ORIGINAL · 8,897</div>${mini("original",g.original)}</div><div><div class="mapping-label">REGROUPED · 10,612</div>${g.historical.map(j=>mini("historical",j)).join("")}</div></div>
      <details><summary>Latest corresponding missions (${g.latest.length})</summary>${g.latest.map(j=>mini("latest",j)).join("")}</details>
      <div class="review-row"><label for="review-${i}">My review</label><select id="review-${i}" data-review="${esc(id)}"><option value="">Unreviewed</option><option value="merge" ${note.decision==="merge"?"selected":""}>Suggest merging</option><option value="keep" ${note.decision==="keep"?"selected":""}>Keep separate</option><option value="uncertain" ${note.decision==="uncertain"?"selected":""}>Needs inspection</option></select><input aria-label="Review note for original mission ${g.original+1}" data-note="${esc(id)}" placeholder="Optional note" value="${esc(note.text || "")}"><span class="saved">${note.updated?"Saved in this browser":""}</span></div></article>`;
  }).join("");
}
function renderAnnotations() {
  const highlighted = new Set(current.splits.flatMap(g=>g.historical));
  $("annotations").innerHTML = Object.keys(names).map(name => {
    const t = current.tracks[name], byID = new Map(t.actions.map((a,i)=>[a.id,{...a,number:i+1}]));
    return `<section class="column ${name}"><h3>${names[name]}<br><small class="muted">${t.missions.length} missions · ${t.actions.length} actions</small></h3>${t.missions.map((m,i)=>
      `<div class="mission-card ${name==="historical"&&highlighted.has(i)?"changed":""}"><button class="mission-title" data-frame="${m.start}">M${i+1}. ${esc(m.label)}</button><span class="mission-range">Frames ${m.start}–${m.end}</span><details class="actions" open><summary>${m.actions.length} atomic action${m.actions.length===1?"":"s"}</summary>${m.actions.map(id=>{
        const a=byID.get(id); return a ? `<button class="action" data-frame="${a.start}">A${a.number}. ${esc(a.label)}<small>${a.start}–${a.end}</small></button>` : "";
      }).join("")}</details></div>`).join("")}</section>`;
  }).join("");
}
function saveReview(target) {
  const id = target.dataset.review || target.dataset.note, row = target.closest(".review-row");
  notes[id] = {episode:current.key, original_mission:Number(id.split("::").pop())+1,
               decision:row.querySelector("select").value, text:row.querySelector("input").value, updated:new Date().toISOString()};
  try { localStorage.setItem(store,JSON.stringify(notes)); row.querySelector(".saved").textContent="Saved in this browser"; }
  catch (_) { row.querySelector(".saved").textContent="Storage unavailable; export your review."; }
}
function renderOverview() {
  const s=catalog.summary;
  $("population").textContent=`16 datasets · 6,600 episodes · 3 snapshots`;
  $("global-stats").innerHTML=[
    [s.increased_episodes,"Episodes with more missions",`+${fmt(s.gross_increase)} missions before offsets`],
    [s.net_increase,"Net mission increase",`+${fmt(s.gross_increase)} − ${fmt(s.gross_decrease)} = +${fmt(s.net_increase)}`],
    [s.stable_increased_episodes,"Increased with unchanged action ranges",`+${fmt(s.stable_gross_increase)} missions in this group`],
    [s.reduced_since_historical,"Missions reduced since 10,612",`${fmt(s.totals.latest.missions)} missions in the latest labels`]
  ].map(([n,label,sub])=>`<div class="stat"><span>${label}</span><strong>${fmt(n)}</strong><span>${sub}</span></div>`).join("");
  $("dataset-table").innerHTML=`<table><thead><tr><th>Dataset</th><th>Episodes</th><th>Original</th><th>Regrouped</th><th>Latest</th><th>Net increase</th><th>Increased episodes</th></tr></thead><tbody>${catalog.datasets.map(d=>`<tr><td>${esc(d.label)}</td><td>${fmt(d.episodes)}</td><td>${fmt(d.missions.original)}</td><td>${fmt(d.missions.historical)}</td><td>${fmt(d.missions.latest)}</td><td>${d.net_increase>0?"+":""}${fmt(d.net_increase)}</td><td>${fmt(d.increased)}</td></tr>`).join("")}</tbody></table>`;
}
document.addEventListener("click", event => {
  const button=event.target.closest("[data-key], [data-frame]");
  if (button?.dataset.key) loadEpisode(button.dataset.key).catch(fail);
  else if (button?.dataset.frame !== undefined) seek(button.dataset.frame);
});
document.addEventListener("change", event => {
  if (event.target.matches("[data-review], [data-note]")) saveReview(event.target);
});
$("scope").addEventListener("change",()=>renderList());
$("sort").addEventListener("change",()=>renderList());
let searchTimer;
$("search").addEventListener("input",()=>{clearTimeout(searchTimer); searchTimer=setTimeout(()=>renderList(),150);});
for (const [id,direction] of [["prev",-1],["next",1]]) $(id).onclick=()=>{
  const index=filtered.findIndex(r=>r.key===current?.key), row=filtered[index+direction];
  if(row) loadEpisode(row.key).catch(fail);
};
$("seek-frame").onclick=()=>seek($("frame-input").value);
$("frame-input").onkeydown=event=>{if(event.key==="Enter")seek(event.target.value);};
$("back-frame").onclick=()=>seek(Number($("frame-input").value)-1);
$("next-frame").onclick=()=>seek(Number($("frame-input").value)+1);
$("video").addEventListener("loadedmetadata",()=>{seek(pendingFrame);$("video-status").textContent="";});
$("video").addEventListener("timeupdate",updateFrame);
$("video").addEventListener("seeked",updateFrame);
$("video").addEventListener("error",()=>{$("video-status").textContent="Video could not load. The annotation comparison remains available.";});
$("export-notes").onclick=()=>{
  const payload={comparison:"8897-to-10612-with-latest-10373",exported_at:new Date().toISOString(),reviews:Object.values(notes)};
  const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));
  const link=document.createElement("a");link.href=url;link.download="mission-review.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
(async()=>{
  catalog=await fetchJSON("data/index.json");renderOverview();
  const preferred=new URLSearchParams(location.search).get("episode") || "bridge_v2/1046/2133";
  const row=catalog.episodes.find(r=>r.key===preferred);
  if(row && !matches(row,$("scope").value))$("scope").value="all";
  renderList(preferred);
})().catch(fail);

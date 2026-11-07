"use strict";

// Source annotations and model predictions are separate, explicitly labelled views.
(async () => {
  const explorer = document.querySelector(".intent-explorer");
  if (!explorer) return;
  let data;
  try {
    const response = await fetch("static/data/gallery.json?v=20261107-explorer-1");
    if (!response.ok) throw new Error("Gallery unavailable");
    data = await response.json();
  } catch { return; } // The static tiles remain working image links.

  const escape = (value) => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const entries = new Map(data.items.map(item => [item.id, item]));
  const comparisons = data.items.filter(item => item.kind === "comparison");
  const tiles = [...explorer.querySelectorAll(".episode-tile")];
  const detail = explorer.querySelector(".explorer-detail");
  const dialog = document.querySelector(".gallery-modal");
  const modalBody = dialog.querySelector(".gallery-modal-body");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const pauseButton = explorer.querySelector("[data-gallery-pause]");
  const sourceSelect = explorer.querySelector("[data-gallery-source]");
  const modeButtons = [...explorer.querySelectorAll("[data-gallery-mode]")];
  let selected = data.default;
  let activeView = 0;
  let modalView = 0;
  let mode = "all";
  let paused = reduced.matches || Boolean(navigator.connection?.saveData);
  let hovered = null;
  let rotation = 0;
  let modalOrigin = null;
  const visible = new Set();

  const meta = item => item.kind === "comparison"
    ? `Selected test example · ${item.cutoff}% of action observed`
    : `Dataset annotation · Episode ${item.episode}`;
  const context = item => item.context ? `<p class="detail-context">${escape(item.context)}</p>` : "";
  const truth = item => `<div class="detail-truth"><div><small>Annotated action</small><p>${escape(item.action)}</p></div><div><small>Annotated mission</small><p>${escape(item.mission)}</p></div></div>`;
  function predictions(item) {
    if (!item.predictions) return "";
    return `<div class="predictions-heading"><h4>VLM predictions</h4><span>Same observations and execution context</span></div><div class="prediction-grid">${item.predictions.map(p => `<article class="prediction-card ${p.model === "tuned" ? "ours" : ""}"><h5>${escape(p.label)}</h5>${["action", "mission"].map(part => `<div class="prediction-output"><small>Ongoing ${part}</small><p><span class="prediction-verdict" role="img" aria-label="${p[part + "Match"] ? "Matches annotation" : "Differs from annotation"}">${p[part + "Match"] ? "✓" : "×"}</span>${escape(p[part])}</p></div>`).join("")}</article>`).join("")}</div>`;
  }
  const viewButtons = (item, current, modal = false) => `<div class="detail-view" role="group" aria-label="Camera view">${item.views.map((v, i) => `<button type="button" data-${modal ? "modal" : "detail"}-view="${i}" aria-pressed="${i === current}">${escape(v.name)}</button>`).join("")}</div>`;
  function frames(item, current, modal = false) {
    const v = item.views[current];
    return `<div class="detail-frames" style="--frame-count:${v.frames.length}">${v.frames.map((src, i) => `<button type="button" class="detail-frame" data-${modal ? "modal" : "detail"}-frame="${i}" aria-label="Enlarge ${escape(v.name.toLowerCase())} observation ${i + 1} at ${v.times[i]} seconds"${modal ? ' aria-pressed="false"' : ""}><img src="${escape(src)}" alt="${escape(item.title)} — ${escape(v.name.toLowerCase())} observation ${i + 1}" loading="lazy"><span>${v.times[i].toFixed(1)} s</span></button>`).join("")}</div>`;
  }
  function drawConnector() {
    const tile = tiles.find(t => t.dataset.episode === selected);
    const svg = explorer.querySelector(".explorer-connector");
    if (!tile || tile.hidden) { svg.innerHTML = ""; return; }
    const a = tile.getBoundingClientRect(), b = detail.getBoundingClientRect(), e = explorer.getBoundingClientRect();
    const left = a.left - e.left, right = a.right - e.left, top = a.bottom - e.top;
    const bottom = b.top - e.top, endLeft = b.left - e.left + 24, endRight = b.right - e.left - 24;
    svg.setAttribute("viewBox", `0 0 ${e.width} ${e.height}`);
    svg.innerHTML = `<path d="M ${left} ${top} L ${endLeft} ${bottom} L ${endRight} ${bottom} L ${right} ${top} Z"/>`;
  }
  function renderDetail() {
    const item = entries.get(selected);
    detail.innerHTML = `<div class="detail-heading"><div><span class="detail-source">${escape(item.source)}</span><h3 id="explorer-detail-title">${escape(item.title)}</h3><p class="detail-meta">${meta(item)}</p></div><div class="detail-navigation"><button type="button" data-example-step="-1" aria-label="Previous model comparison">‹</button><button type="button" data-example-step="1" aria-label="Next model comparison">›</button></div></div>${context(item)}<div class="detail-media-toolbar">${viewButtons(item, activeView)}<button type="button" class="explorer-enlarge" data-enlarge>↗ Enlarge</button></div>${frames(item, activeView)}${item.note ? `<p class="detail-note">${escape(item.note)}</p>` : ""}${truth(item)}${predictions(item)}<div class="comparison-picks" role="group" aria-label="Selected model comparisons">${comparisons.map((x, i) => `<button type="button" data-comparison="${x.id}" aria-pressed="${x.id === selected}">${i + 1} · ${escape(x.title)}</button>`).join("")}</div>`;
    tiles.forEach(t => t.setAttribute("aria-current", String(t.dataset.episode === selected)));
    requestAnimationFrame(drawConnector);
  }
  function select(id) {
    if (!entries.has(id)) return;
    selected = id; activeView = 0;
    renderDetail();
  }
  function showModalFrame(index) {
    const item = entries.get(selected), view = item.views[modalView];
    const video = modalBody.querySelector("video"), image = modalBody.querySelector(".gallery-modal-stage > img");
    video.pause(); video.hidden = true; image.hidden = false;
    image.src = view.frames[index]; image.alt = `${item.title} — ${view.name} observation ${index + 1}`;
    modalBody.querySelector(".modal-replay").hidden = false;
    modalBody.querySelectorAll("[data-modal-frame]").forEach(b => b.setAttribute("aria-pressed", String(Number(b.dataset.modalFrame) === index)));
  }
  function renderModal(frameIndex = null) {
    const item = entries.get(selected), view = item.views[modalView];
    modalBody.querySelector("video")?.pause();
    dialog.querySelector(".gallery-modal-bar span").textContent = `${item.source} · Episode ${item.episode}`;
    modalBody.innerHTML = `<h3 id="gallery-modal-title">${escape(item.title)}</h3><p class="detail-meta">${meta(item)}${view.speed > 1.01 ? ` · Clip ${view.speed}×` : ""}</p><div class="detail-media-toolbar">${viewButtons(item, modalView, true)}</div><div class="gallery-modal-stage"><video controls muted playsinline loop preload="metadata" poster="${escape(view.frames[0])}" src="${escape(view.video)}" aria-label="${escape(item.title)} — ${escape(view.name)} clip"></video><img hidden alt=""><button type="button" class="modal-replay" hidden>▶ Play clip</button></div>${frames(item, modalView, true)}${item.note ? `<p class="detail-note">${escape(item.note)}</p>` : ""}${context(item)}${truth(item)}${predictions(item)}`;
    if (frameIndex !== null) showModalFrame(frameIndex);
    else if (!reduced.matches) modalBody.querySelector("video").play().catch(() => {});
  }
  function openModal(origin, frameIndex = null) {
    modalView = activeView;
    modalOrigin = origin;
    renderModal(frameIndex);
    dialog.showModal(); dialog.scrollTop = 0;
    document.body.classList.add("dialog-open");
    updateMotion();
    if (!reduced.matches && origin && dialog.animate) {
      const from = origin.getBoundingClientRect(), to = dialog.getBoundingClientRect();
      dialog.animate([
        { opacity: .3, transform: `translate(${from.x + from.width / 2 - to.x - to.width / 2}px, ${from.y + from.height / 2 - to.y - to.height / 2}px) scale(${Math.max(.18, Math.min(.5, from.width / to.width))})` },
        { opacity: 1, transform: "translate(0,0) scale(1)" }
      ], { duration: 420, easing: "cubic-bezier(.2,.75,.2,1)" });
    }
  }
  detail.addEventListener("click", event => {
    const target = event.target.closest("button"); if (!target) return;
    if (target.dataset.comparison) { select(target.dataset.comparison); detail.querySelector(`[data-comparison="${selected}"]`).focus({preventScroll:true}); }
    else if (target.dataset.exampleStep) {
      const index = comparisons.findIndex(x => x.id === selected);
      select(comparisons[(Math.max(0, index) + Number(target.dataset.exampleStep) + comparisons.length) % comparisons.length].id);
      detail.querySelector(`[data-example-step="${target.dataset.exampleStep}"]`).focus({preventScroll:true});
    } else if (target.dataset.detailView !== undefined) {
      activeView = Number(target.dataset.detailView); renderDetail(); detail.querySelector(`[data-detail-view="${activeView}"]`).focus({preventScroll:true});
    } else if (target.dataset.detailFrame !== undefined) openModal(target, Number(target.dataset.detailFrame));
    else if (target.hasAttribute("data-enlarge")) openModal(target);
  });
  modalBody.addEventListener("click", event => {
    const b = event.target.closest("button"); if (!b) return;
    if (b.dataset.modalView !== undefined) { modalView = Number(b.dataset.modalView); renderModal(); modalBody.querySelector(`[data-modal-view="${modalView}"]`).focus(); }
    else if (b.dataset.modalFrame !== undefined) showModalFrame(Number(b.dataset.modalFrame));
    else if (b.classList.contains("modal-replay")) {
      const v = modalBody.querySelector("video"); modalBody.querySelector(".gallery-modal-stage > img").hidden = true; v.hidden = false; b.hidden = true;
      modalBody.querySelectorAll("[data-modal-frame]").forEach(t => t.setAttribute("aria-pressed", "false"));
      v.play().catch(() => {});
    }
  });
  dialog.querySelector(".gallery-modal-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  });
  dialog.addEventListener("close", () => {
    modalBody.querySelector("video")?.pause(); modalBody.replaceChildren();
    document.body.classList.remove("dialog-open");
    if (modalOrigin?.isConnected) modalOrigin.focus({preventScroll:true});
    updateMotion();
  });
  function playTile(tile) {
    let v = tile.querySelector("video");
    if (!v) {
      v = document.createElement("video"); v.muted = true; v.defaultMuted = true; v.loop = true; v.playsInline = true; v.preload = "none";
      v.setAttribute("aria-hidden", "true"); v.tabIndex = -1;
      v.src = entries.get(tile.dataset.episode).views[0].video;
      tile.insertBefore(v, tile.children[1]);
      v.addEventListener("playing", () => tile.classList.add("is-playing"));
      v.addEventListener("error", () => tile.classList.remove("is-playing"));
    }
    if (v.paused) v.play().catch(() => tile.classList.remove("is-playing"));
  }
  function updateMotion() {
    const allowed = !paused && !document.hidden && !dialog.open;
    const pool = tiles.filter(t => visible.has(t) && !t.hidden);
    const active = new Set();
    if (allowed && pool.length) {
      if (hovered && pool.includes(hovered)) active.add(hovered);
      for (let i = 0; i < Math.min(4, pool.length); i++) active.add(pool[(rotation + i) % pool.length]);
      while (active.size > 4) active.delete([...active].at(-1));
    }
    tiles.forEach(tile => {
      if (active.has(tile)) playTile(tile);
      else { tile.querySelector("video")?.pause(); tile.classList.remove("is-playing"); }
    });
    pauseButton.textContent = paused ? "▶ Play" : "Ⅱ Pause";
    pauseButton.setAttribute("aria-label", paused ? "Play gallery previews" : "Pause gallery previews");
    pauseButton.setAttribute("aria-pressed", String(!paused));
  }
  const observer = new IntersectionObserver(changes => {
    changes.forEach(x => x.isIntersecting ? visible.add(x.target) : visible.delete(x.target)); updateMotion();
  }, {threshold: .15});
  tiles.forEach(tile => {
    observer.observe(tile);
    tile.addEventListener("click", event => {
      if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); select(tile.dataset.episode); openModal(tile);
    });
    for (const name of ["mouseenter", "focus"]) tile.addEventListener(name, () => { hovered = tile; updateMotion(); });
    for (const name of ["mouseleave", "blur"]) tile.addEventListener(name, () => { if (hovered === tile) hovered = null; updateMotion(); });
  });
  function filter() {
    const source = sourceSelect.value;
    tiles.forEach(tile => { const item = entries.get(tile.dataset.episode); tile.hidden = (mode === "comparison" && item.kind !== "comparison") || (source !== "all" && item.source !== source); });
    modeButtons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.galleryMode === mode)));
    updateMotion(); requestAnimationFrame(drawConnector);
  }
  modeButtons.forEach(b => b.addEventListener("click", () => { mode = b.dataset.galleryMode; sourceSelect.value = "all"; filter(); }));
  sourceSelect.addEventListener("change", () => { mode = "all"; filter(); });
  pauseButton.addEventListener("click", () => { paused = !paused; updateMotion(); });
  reduced.addEventListener("change", () => { paused = reduced.matches; updateMotion(); });
  document.addEventListener("visibilitychange", updateMotion);
  const timer = setInterval(() => { rotation += 4; updateMotion(); }, 7000);
  window.addEventListener("pagehide", () => { clearInterval(timer); tiles.forEach(t => t.querySelector("video")?.pause()); });
  new ResizeObserver(() => requestAnimationFrame(drawConnector)).observe(explorer);
  renderDetail(); explorer.classList.add("gallery-ready");
})();

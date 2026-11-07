/* Native video film strips, projected onto a gently curved moving wall. */
(() => {
  "use strict";
  const wall = document.querySelector(".film-wall");
  if (!wall) return;
  const spotlight = wall.querySelector(".film-spotlight");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const tiles = [...wall.querySelectorAll(".film-tile")].map((button, index) => ({
    button, video: button.querySelector("video"), row: Math.floor(index / 7), column: index % 7,
    x: 0, visible: false
  }));
  const rowOffsets = [2, .55, 1.2, .05];
  const rowSpeeds = [19, 23, 20, 25];
  const drift = [0, 0, 0, 0];
  const pendingPlay = new WeakSet();
  let items = new Map();
  let width = 0, height = 0, tileWidth = 0, tileHeight = 0, stride = 0;
  let inView = false, active = null, pinned = false, frame = 0, lastTime = 0, mediaTime = 0;
  let hoverTimer = 0, closeTimer = 0, pendingTile = null;
  let pointer = null, sourceRegion = null;

  const clamp = (n, lo, hi) => Math.min(Math.max(n, lo), Math.max(lo, hi));
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function play(video) {
    if (!video.src && video.dataset.src) video.src = video.dataset.src;
    if (!video.paused || pendingPlay.has(video)) return;
    pendingPlay.add(video);
    const promise = video.play();
    if (promise) promise.catch(() => {}).finally(() => pendingPlay.delete(video));
    else pendingPlay.delete(video);
  }
  function syncPlayback() {
    const available = inView && !document.hidden;
    tiles.forEach(tile => {
      // Every visible clip plays; a lifted clip continues in the spotlight.
      if (available && !reducedMotion.matches && tile.visible && tile !== active) play(tile.video);
      else tile.video.pause();
    });
    const video = spotlight.querySelector("video");
    if (video) {
      if (available) play(video);
      else video.pause();
    }
  }
  function project() {
    const rowStep = tileHeight + 15;
    const top = (height - (rowStep * 4 - 15)) / 2;
    tiles.forEach(tile => {
      const cycle = stride * 7;
      const x = ((tile.column + rowOffsets[tile.row]) * stride + drift[tile.row]) % cycle - stride;
      const n = (x + tileWidth / 2 - width / 2) / (width / 2 + tileWidth / 2);
      const curve = clamp(n, -1.5, 1.5);
      const scale = 1 - .09 * Math.min(1.6, curve * curve);
      const y = top + tile.row * rowStep + (tile.row - 1.5) * curve * curve * 19;
      tile.x = x;
      tile.visible = x + tileWidth > 0 && x < width;
      tile.button.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) perspective(900px) rotateY(${-curve * 22}deg) rotateZ(${curve * (tile.row - 1.5) * 2.6}deg) scale(${scale})`;
    });
  }
  function tick(time) {
    frame = 0;
    const elapsed = lastTime ? Math.min(time - lastTime, 50) / 1000 : 0;
    lastTime = time;
    if (!active) {
      drift.forEach((value, row) => { drift[row] = (value + elapsed * rowSpeeds[row]) % (stride * 7); });
      project();
    }
    if (time - mediaTime > 300) { syncPlayback(); mediaTime = time; }
    if (inView && !document.hidden && !reducedMotion.matches && !active) frame = requestAnimationFrame(tick);
  }
  function updateMotion() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    lastTime = 0;
    syncPlayback();
    if (inView && !document.hidden && !reducedMotion.matches && !active) frame = requestAnimationFrame(tick);
  }

  function renderResults(item) {
    const card = el("section", "film-results");
    card.setAttribute("aria-label", `${item.source}: ${item.kind === "comparison" ? "Model predictions" : "Dataset annotation"}`);
    const close = el("button", "film-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close highlighted film");
    close.addEventListener("click", () => closeSpotlight(true));
    card.append(close, el("span", "film-source", item.source), el("h3", "", item.title));
    if (item.kind === "comparison" && item.predictions?.length) {
      const predictions = el("div", "film-predictions");
      item.predictions.forEach(prediction => {
        const article = el("article", `film-prediction${prediction.model === "tuned" ? " ours" : ""}`);
        article.append(el("h4", "", prediction.label));
        [["OA", "Ongoing action", prediction.action], ["OM", "Ongoing mission", prediction.mission]].forEach(([label, full, text]) => {
          const line = el("p");
          const key = el("b", "", label);
          key.setAttribute("aria-label", full);
          line.append(key, el("span", "", text));
          article.append(line);
        });
        predictions.append(article);
      });
      card.append(predictions);
    } else {
      // These samples have annotations, not recorded model predictions.
      card.append(el("span", "film-annotation-label", "Dataset annotation"));
      const annotations = el("dl", "film-annotation");
      annotations.append(el("dt", "", "Action"), el("dd", "", item.action), el("dt", "", "Mission"), el("dd", "", item.mission));
      card.append(annotations);
    }
    return card;
  }

  function positionSpotlight() {
    if (!active) return;
    const hero = spotlight.querySelector(".film-hero");
    const card = spotlight.querySelector(".film-results");
    const bounds = wall.getBoundingClientRect();
    const source = active.button.getBoundingClientRect();
    const cx = source.left + source.width / 2 - bounds.left;
    const cy = source.top + source.height / 2 - bounds.top;
    const mobile = width <= 700;
    const margin = mobile ? 14 : 24;
    const videoWidth = mobile ? Math.min(390, width - 2 * margin) : Math.min(480, (width - 2 * margin - 20) * .49);
    const videoHeight = mobile ? Math.min(232, videoWidth * .70 + 24) : videoWidth * .75 + 28;
    const cardWidth = mobile ? videoWidth : Math.min(450, width - 2 * margin - 20 - videoWidth);
    hero.style.width = `${videoWidth}px`;
    hero.style.height = `${videoHeight}px`;
    card.style.width = `${cardWidth}px`;
    card.style.maxHeight = `${mobile ? height - videoHeight - 2 * margin - 10 : height - 2 * margin}px`;
    const videoRight = !mobile && cx > width / 2;
    spotlight.classList.toggle("video-right", videoRight);
    const groupWidth = mobile ? videoWidth : videoWidth + cardWidth + 20;
    spotlight.style.width = `${groupWidth}px`;
    const groupHeight = mobile ? videoHeight + card.offsetHeight + 10 : Math.max(videoHeight, card.offsetHeight);
    let left = mobile ? (width - groupWidth) / 2 : cx - videoWidth / 2 - (videoRight ? cardWidth + 20 : 0);
    let top = mobile ? (height - groupHeight) / 2 : cy - groupHeight / 2;
    spotlight.style.left = `${clamp(left, margin, width - groupWidth - margin)}px`;
    spotlight.style.top = `${clamp(top, margin, height - groupHeight - margin)}px`;
  }
  function clearTimers() {
    clearTimeout(hoverTimer);
    clearTimeout(closeTimer);
    pendingTile = null;
  }
  function showSpotlight(tile, pin = false) {
    const item = items.get(tile.button.dataset.episode);
    if (!item) return;
    clearTimers();
    if (active === tile) { pinned = pinned || pin; return; }
    closeSpotlight(false);
    active = tile;
    pinned = pin;
    const source = tile.button.getBoundingClientRect();
    sourceRegion = source;
    const hero = el("figure", "film-hero");
    const frame = el("div", "film-frame");
    const video = el("video");
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.poster = tile.video.poster;
    video.setAttribute("aria-label", item.title);
    video.addEventListener("loadedmetadata", () => {
      if (Number.isFinite(video.duration) && video.duration > 0) video.currentTime = tile.video.currentTime % video.duration;
    }, { once: true });
    video.src = item.views[0].video;
    frame.append(video);
    hero.append(frame);
    const card = renderResults(item);
    spotlight.replaceChildren(hero, card);
    spotlight.hidden = false;
    wall.classList.add("is-inspecting");
    tile.button.classList.add("is-selected");
    tile.button.setAttribute("aria-expanded", "true");
    positionSpotlight();
    if (!reducedMotion.matches) {
      const target = hero.getBoundingClientRect();
      hero.animate([
        { transformOrigin: "0 0", transform: `translate(${source.left - target.left}px, ${source.top - target.top}px) scale(${source.width / target.width}, ${source.height / target.height})` },
        { transformOrigin: "0 0", transform: "none" }
      ], { duration: 360, easing: "cubic-bezier(.2,.8,.2,1)" });
      card.animate([{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "none" }], { duration: 300, easing: "ease-out" });
    }
    updateMotion();
  }
  function closeSpotlight(restoreFocus = false) {
    clearTimers();
    if (!active) return;
    const previous = active;
    spotlight.querySelector("video")?.pause();
    active = null;
    sourceRegion = null;
    pinned = false;
    spotlight.hidden = true;
    spotlight.replaceChildren();
    wall.classList.remove("is-inspecting");
    previous.button.classList.remove("is-selected");
    previous.button.setAttribute("aria-expanded", "false");
    // Focus restoration must not immediately open the film again.
    if (restoreFocus) {
      previous.button.dataset.restoringFocus = "true";
      previous.button.focus({ preventScroll: true });
      delete previous.button.dataset.restoringFocus;
    }
    updateMotion();
  }
  function scheduleClose() {
    clearTimeout(closeTimer);
    if (!pinned) closeTimer = setTimeout(() => {
      if (!pointerInSpotlight()) closeSpotlight();
    }, 260);
  }
  function inside(rect) {
    return pointer && rect && pointer.x >= rect.left && pointer.x <= rect.right && pointer.y >= rect.top && pointer.y <= rect.bottom;
  }
  function pointerInSpotlight() {
    // Preserve the hover while the growing film moves away from its original
    // hit area, and while the pointer crosses the gap to its prediction card.
    return active && inside(wall.getBoundingClientRect()) && (inside(sourceRegion) || inside(spotlight.getBoundingClientRect()));
  }

  tiles.forEach(tile => {
    tile.button.addEventListener("pointerenter", event => {
      pointer = { x: event.clientX, y: event.clientY };
      if (event.pointerType === "touch" || pinned || active === tile) return;
      if (pointerInSpotlight()) { clearTimers(); return; }
      clearTimers();
      pendingTile = tile;
      hoverTimer = setTimeout(() => showSpotlight(tile), active ? 260 : 100);
    });
    tile.button.addEventListener("pointerleave", () => {
      if (pendingTile === tile) { clearTimeout(hoverTimer); pendingTile = null; }
      if (active === tile) scheduleClose();
    });
    tile.button.addEventListener("focus", () => {
      if (!tile.button.dataset.restoringFocus && tile.button.matches(":focus-visible")) showSpotlight(tile, true);
    });
    tile.button.addEventListener("click", () => showSpotlight(tile, true));
  });
  spotlight.addEventListener("pointerenter", clearTimers);
  spotlight.addEventListener("pointerleave", scheduleClose);
  spotlight.addEventListener("focusin", clearTimers);
  wall.addEventListener("pointermove", event => {
    pointer = { x: event.clientX, y: event.clientY };
    if (active && !pinned && !pointerInSpotlight()) scheduleClose();
  });
  wall.addEventListener("pointerleave", () => { pointer = null; clearTimeout(hoverTimer); scheduleClose(); });
  wall.addEventListener("focusout", () => {
    setTimeout(() => { if (!wall.contains(document.activeElement)) closeSpotlight(); }, 0);
  });
  document.addEventListener("pointerdown", event => {
    if (active && !spotlight.contains(event.target) && !event.target.closest(".film-tile")) closeSpotlight();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && active) { event.preventDefault(); closeSpotlight(true); }
  });
  document.addEventListener("visibilitychange", updateMotion);
  reducedMotion.addEventListener("change", updateMotion);

  function resize() {
    width = wall.clientWidth;
    height = wall.clientHeight;
    tileWidth = Math.max(220, width / 5.45);
    tileHeight = tileWidth / 1.5;
    stride = tileWidth + 18;
    tiles.forEach(tile => {
      tile.button.style.width = `${tileWidth}px`;
      tile.button.style.height = `${tileHeight}px`;
    });
    project();
    positionSpotlight();
    syncPlayback();
  }
  fetch("static/data/gallery.json").then(response => {
    if (!response.ok) throw new Error(`Gallery: ${response.status}`);
    return response.json();
  }).then(data => {
    items = new Map(data.items.map(item => [item.id, item]));
    wall.classList.add("is-ready");
    resize();
    new ResizeObserver(resize).observe(wall);
    new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting;
      if (!inView) closeSpotlight();
      updateMotion();
    }, { threshold: 0 }).observe(wall);
  }).catch(error => {
    console.warn("Film wall could not initialize", error);
  });
})();

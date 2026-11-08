/* Curved, moving films with an inline annotation and model comparison. */
(() => {
  "use strict";
  const wall = document.querySelector(".film-wall");
  if (!wall) return;
  const spotlight = wall.querySelector(".film-spotlight");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const tiles = [...wall.querySelectorAll(".film-tile")].map((button, index) => {
    const video = button.querySelector("video");
    const poster = document.createElement("img");
    poster.className = "film-poster";
    poster.src = video.poster;
    poster.alt = "";
    button.prepend(poster);
    // Keep the still visible until the first decoded frame is available.
    video.addEventListener("loadeddata", () => button.classList.add("has-video-frame"), { once: true });
    return { button, video, row: Math.floor(index / 7), column: index % 7, x: 0, visible: false };
  });
  const rowOffsets = [1.1, .35, 1.65, .8];
  const rowSpeeds = [14, 17, 15, 18];
  const drift = [0, 0, 0, 0];
  const pendingPlay = new WeakSet();
  let items = new Map();
  let width = 0, height = 0, tileWidth = 0, tileHeight = 0, stride = 0;
  let inView = false, active = null, pinned = false, frame = 0, lastTime = 0, mediaTime = 0;
  let hoverTimer = 0, closeTimer = 0, pendingTile = null;
  let pointer = null, sourceRegion = null;
  let introDone = reducedMotion.matches, introInView = false, introElapsed = 0;

  wall.classList.toggle("is-introducing", !introDone);
  const stars = wall.querySelector(".film-stars");
  if (stars) {
    // A stable, sparse field; no particles are drawn over the films.
    let seed = 6600;
    const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    for (let index = 0; index < 140; index++) {
      const star = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      star.setAttribute("cx", (random() * 1360).toFixed(2));
      star.setAttribute("cy", (random() * 680).toFixed(2));
      star.setAttribute("r", (.4 + random() * .5).toFixed(2));
      star.setAttribute("fill", "#e2e4e8");
      star.setAttribute("opacity", (.18 + random() * .32).toFixed(2));
      stars.append(star);
    }
  }

  function finishIntro() {
    introDone = true;
    wall.classList.remove("is-introducing");
    wall.style.removeProperty("--film-reveal");
  }

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
      if (available && introDone && !reducedMotion.matches && tile.visible && tile !== active) play(tile.video);
      else tile.video.pause();
    });
    const video = spotlight.querySelector("video");
    if (video) {
      if (available) play(video);
      else video.pause();
    }
  }
  function project() {
    const rowStep = tileHeight + 16;
    const top = (height - (rowStep * 4 - 16)) / 2;
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
    const elapsedMs = lastTime ? time - lastTime : 0;
    const elapsed = Math.min(elapsedMs, 50) / 1000;
    lastTime = time;
    if (!introDone && introInView) {
      introElapsed += elapsedMs;
      const reveal = clamp((introElapsed - 1500) / 1500, 0, 1);
      wall.style.setProperty("--film-reveal", reveal.toFixed(3));
      if (reveal === 1) finishIntro();
    }
    if (!active) {
      drift.forEach((value, row) => { drift[row] = (value + elapsed * rowSpeeds[row]) % (stride * 7); });
      project();
    }
    if (time - mediaTime > 300) { syncPlayback(); mediaTime = time; }
    if (inView && !document.hidden && !reducedMotion.matches && !active) frame = requestAnimationFrame(tick);
  }
  function updateMotion() {
    if (reducedMotion.matches && !introDone) finishIntro();
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    lastTime = 0;
    syncPlayback();
    if (inView && !document.hidden && !reducedMotion.matches && !active) frame = requestAnimationFrame(tick);
  }

  function resultLines(action, mission) {
    const lines = el("div", "film-result-lines");
    [["OA", "Ongoing action", action], ["OM", "Ongoing mission", mission]].forEach(([label, full, text]) => {
      const line = el("p");
      const key = el("b", "", label);
      key.setAttribute("aria-label", full);
      line.append(key, el("span", "", text));
      lines.append(line);
    });
    return lines;
  }
  function renderAnnotation(item) {
    const annotation = el("section", "film-groundtruth");
    annotation.setAttribute("aria-label", "Dataset annotation");
    annotation.append(el("h4", "", "Annotation"), resultLines(item.action, item.mission));
    return annotation;
  }
  function renderResults(item) {
    const card = el("section", "film-results");
    card.setAttribute("aria-label", `${item.source}: four model predictions`);
    const predictions = el("div", "film-predictions");
    item.predictions.forEach(prediction => {
      const article = el("article", `film-prediction${prediction.model === "tuned" ? " ours" : ""}`);
      article.append(el("h4", "", prediction.label), resultLines(prediction.action, prediction.mission));
      predictions.append(article);
    });
    card.append(predictions);
    return card;
  }

  function positionSpotlight() {
    if (!active) return;
    const hero = spotlight.querySelector(".film-hero");
    const card = spotlight.querySelector(".film-results");
    const videoFrame = hero.querySelector(".film-frame");
    const bounds = wall.getBoundingClientRect();
    const source = active.button.getBoundingClientRect();
    const cx = source.left + source.width / 2 - bounds.left;
    const cy = source.top + source.height / 2 - bounds.top;
    const mobile = matchMedia("(max-width: 700px)").matches;
    const margin = mobile ? 10 : 22;
    const padding = mobile ? 12 : 16;
    const gap = mobile ? 10 : 18;
    const groupWidth = Math.min(mobile ? 440 : 900, width - 2 * margin);
    const contentWidth = groupWidth - 2 * padding - 2;
    const videoWidth = mobile ? contentWidth : (contentWidth - gap) * .43;
    const cardWidth = mobile ? contentWidth : contentWidth - videoWidth - gap;
    const videoHeight = mobile ? Math.min(180, videoWidth * .64) : Math.min(265, videoWidth * .75 + 20);
    hero.style.width = `${videoWidth}px`;
    hero.style.height = "auto";
    videoFrame.style.height = `${videoHeight}px`;
    card.style.width = `${cardWidth}px`;
    card.style.maxHeight = mobile ? "none" : `${height - 2 * margin - 2 * padding}px`;
    spotlight.style.width = `${groupWidth}px`;
    spotlight.style.maxHeight = `${height - 2 * margin}px`;
    const groupHeight = Math.min(spotlight.offsetHeight, height - 2 * margin);
    const left = mobile ? (width - groupWidth) / 2 : cx - groupWidth / 2;
    const top = mobile ? margin : cy - groupHeight / 2;
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
    if (!item || item.predictions?.length !== 4) return;
    finishIntro();
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
    // A lifted film starts with the complete action, independent of wall playback.
    video.src = item.views[0].video;
    frame.append(video);
    hero.append(el("span", "film-source", item.source), frame, renderAnnotation(item));
    const card = renderResults(item);
    const close = el("button", "film-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close highlighted film");
    close.addEventListener("click", () => closeSpotlight(true));
    spotlight.replaceChildren(hero, card, close);
    spotlight.scrollTop = 0;
    spotlight.hidden = false;
    wall.classList.add("is-inspecting");
    tile.button.classList.add("is-selected");
    tile.button.setAttribute("aria-expanded", "true");
    positionSpotlight();
    if (!reducedMotion.matches) {
      const target = frame.getBoundingClientRect();
      frame.animate([
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
      if (!introDone || event.pointerType === "touch" || pinned || active === tile) return;
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
    tileHeight = (height - 80) / 4;
    tileWidth = Math.max(210, tileHeight * 1.62, width / 6);
    stride = tileWidth + 16;
    tiles.forEach(tile => {
      tile.button.style.width = `${tileWidth}px`;
      tile.button.style.height = `${tileHeight}px`;
    });
    project();
    positionSpotlight();
    syncPlayback();
  }
  fetch("static/data/gallery.json?v=20261108-diverse-1").then(response => {
    if (!response.ok) throw new Error(`Gallery: ${response.status}`);
    return response.json();
  }).then(data => {
    items = new Map(data.items.map(item => [item.id, item]));
    wall.classList.add("is-ready");
    resize();
    new ResizeObserver(resize).observe(wall);
    new IntersectionObserver(entries => {
      const entry = entries[entries.length - 1];
      inView = entry.isIntersecting;
      introInView = entry.intersectionRatio >= .35;
      if (!inView) closeSpotlight();
      updateMotion();
    }, { threshold: [0, .35] }).observe(wall);
  }).catch(error => {
    finishIntro();
    console.warn("Film wall could not initialize", error);
  });
})();

(() => {
  "use strict";
  const data = window.PANDA_REVIEW_DATA;
  if (!data || !Array.isArray(data.episodes)) throw new Error("Missing data.js");
  const storageKey = "panda-subtask-review-v1";
  const colors = ["#3867d6", "#9b59b6", "#e67e22", "#16a085", "#c0392b", "#2980b9", "#7f8c8d"];
  const $ = id => document.getElementById(id);
  const video = $("video");
  const timeline = $("timeline");
  let state = loadState();
  let currentIndex = 0;
  let selectedSegment = 0;
  let selectedBoundary = null;
  let draggingBoundary = null;
  let pendingPreviewFrame = null;
  let previewAnimationFrame = null;

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function episodeKey(ep) { return `${ep.task_id}/${ep.episode_id}`; }
  function loadState() {
    try { return JSON.parse(localStorage.getItem(storageKey)) || {}; }
    catch (_) { return {}; }
  }
  function persist() { localStorage.setItem(storageKey, JSON.stringify(state)); updateProgress(); }
  function baseSegments(ep) { return clone(ep.segments); }
  function record(ep) {
    const key = episodeKey(ep);
    if (!state[key]) state[key] = { reviewed: false, segments: baseSegments(ep), updated_at: null };
    return state[key];
  }
  function normalizeSegments(ep, segments) {
    segments.sort((a, b) => a.start_frame - b.start_frame);
    segments[0].start_frame = 0;
    for (let i = 1; i < segments.length; i++) segments[i].start_frame = segments[i - 1].end_frame + 1;
    segments[segments.length - 1].end_frame = ep.frame_count - 1;
    segments.forEach((s, i) => { s.subtask_id = `subtask_${i + 1}`; });
  }
  function touch(ep) { const r = record(ep); r.updated_at = new Date().toISOString(); persist(); }
  function frameNow(ep) { return Math.max(0, Math.min(ep.frame_count - 1, Math.round(video.currentTime * ep.fps))); }
  function seekFrame(ep, frame) { video.currentTime = Math.max(0, Math.min(ep.frame_count - 1, frame)) / ep.fps; }
  function pct(frame, ep) { return 100 * frame / Math.max(1, ep.frame_count - 1); }

  function previewFrame(ep, frame) {
    pendingPreviewFrame = Math.max(0, Math.min(ep.frame_count - 1, frame));
    $("frame-readout").textContent = `frame ${pendingPreviewFrame} / ${ep.frame_count - 1}`;
    $("playhead").style.left = `${pct(pendingPreviewFrame, ep)}%`;
    if (previewAnimationFrame != null) return;
    previewAnimationFrame = requestAnimationFrame(() => {
      const target = pendingPreviewFrame;
      pendingPreviewFrame = null;
      previewAnimationFrame = null;
      if (target != null) seekFrame(ep, target);
    });
  }

  function renderDirectory() {
    const groups = new Map();
    data.episodes.forEach((ep, index) => {
      if (!groups.has(ep.original_task)) groups.set(ep.original_task, []);
      groups.get(ep.original_task).push({ ep, index });
    });
    const root = $("task-list"); root.textContent = "";
    groups.forEach((items, task) => {
      const details = document.createElement("details"); details.className = "task-group";
      const summary = document.createElement("summary"); summary.textContent = `${task} (${items.length})`; details.appendChild(summary);
      items.forEach(({ ep, index }) => {
        const button = document.createElement("button");
        button.className = "episode-button"; button.dataset.index = index;
        const dot = document.createElement("span"); dot.className = `status-dot ${ep.segmentation_status === "ok" ? "ok" : ""}`;
        const text = document.createElement("span"); text.textContent = `Ep ${ep.episode_id} · ${ep.source_split}`;
        button.append(dot, text); button.addEventListener("click", () => selectEpisode(index)); details.appendChild(button);
      });
      root.appendChild(details);
    });
  }

  function renderLabels() {
    const list = $("label-options"); list.textContent = "";
    data.label_options.forEach(value => { const option = document.createElement("option"); option.value = value; list.appendChild(option); });
  }

  function renderTimeline() {
    const ep = data.episodes[currentIndex], segments = record(ep).segments;
    const track = $("segments-track"); track.textContent = "";
    segments.forEach((segment, index) => {
      const block = document.createElement("div"); block.className = `segment-block ${index === selectedSegment ? "selected" : ""}`; block.dataset.segment = index;
      block.style.left = `${pct(segment.start_frame, ep)}%`;
      block.style.width = `${100 * (segment.end_frame - segment.start_frame + 1) / ep.frame_count}%`;
      block.style.background = colors[index % colors.length]; block.title = segment.subtask;
      const label = document.createElement("span"); label.textContent = `${index + 1}. ${segment.subtask}`; block.appendChild(label);
      block.addEventListener("click", event => { event.stopPropagation(); selectedSegment = index; renderTimeline(); renderEditor(); });
      track.appendChild(block);
      if (index < segments.length - 1) {
        const handle = document.createElement("div"); handle.className = `boundary-handle ${index === selectedBoundary ? "selected" : ""}`;
        handle.style.left = `${pct(segment.end_frame + 0.5, ep)}%`; handle.dataset.boundary = index;
        handle.addEventListener("pointerdown", event => {
          event.preventDefault(); event.stopPropagation();
          video.pause();
          draggingBoundary = { index, pointerId: event.pointerId };
          selectedBoundary = index;
          document.querySelectorAll(".boundary-handle.selected").forEach(item => item.classList.remove("selected"));
          handle.classList.add("selected");
          handle.setPointerCapture(event.pointerId);
          previewFrame(ep, segment.end_frame);
          updateBoundaryText();
        });
        track.appendChild(handle);
      }
    });
    $("last-frame-label").textContent = `${ep.frame_count - 1}`;
    updatePlayhead(); updateBoundaryText();
  }

  function moveBoundaryFromPointer(clientX) {
    if (selectedBoundary == null) return;
    const ep = data.episodes[currentIndex], r = record(ep), rect = timeline.getBoundingClientRect();
    const raw = Math.round((clientX - rect.left) / rect.width * (ep.frame_count - 1));
    const left = r.segments[selectedBoundary], right = r.segments[selectedBoundary + 1];
    const frame = Math.max(left.start_frame, Math.min(right.end_frame - 1, raw));
    left.end_frame = frame; right.start_frame = frame + 1;
    const blocks = $("segments-track").querySelectorAll(".segment-block");
    blocks.forEach((block, index) => {
      const segment = r.segments[index];
      block.style.left = `${pct(segment.start_frame, ep)}%`;
      block.style.width = `${100 * (segment.end_frame - segment.start_frame + 1) / ep.frame_count}%`;
    });
    const handle = $("segments-track").querySelector(`.boundary-handle[data-boundary="${selectedBoundary}"]`);
    if (handle) handle.style.left = `${pct(frame + 0.5, ep)}%`;
    previewFrame(ep, frame);
  }

  function finishBoundaryDrag(event) {
    if (!draggingBoundary || (event && event.pointerId !== draggingBoundary.pointerId)) return;
    const ep = data.episodes[currentIndex];
    draggingBoundary = null;
    touch(ep);
    renderTimeline();
    renderEditor();
  }

  function renderEditor() {
    const ep = data.episodes[currentIndex], segments = record(ep).segments, root = $("segment-editor"); root.textContent = "";
    segments.forEach((segment, index) => {
      const row = document.createElement("div"); row.className = `segment-row ${index === selectedSegment ? "selected" : ""}`; row.style.setProperty("--segment-color", colors[index % colors.length]);
      const number = document.createElement("div"); number.className = "segment-index"; number.textContent = `S${index + 1}`;
      const input = document.createElement("input"); input.className = "segment-label"; input.value = segment.subtask; input.setAttribute("list", "label-options");
      input.addEventListener("change", () => { segment.subtask = input.value.trim() || segment.subtask; touch(ep); renderTimeline(); });
      const range = document.createElement("div"); range.className = "segment-range"; range.textContent = `frames ${segment.start_frame}–${segment.end_frame}`;
      row.append(number, input, range); row.addEventListener("click", event => { if (event.target !== input) { selectedSegment = index; renderTimeline(); renderEditor(); } }); root.appendChild(row);
    });
  }

  function selectEpisode(index) {
    currentIndex = Math.max(0, Math.min(data.episodes.length - 1, index)); selectedSegment = 0; selectedBoundary = null;
    const ep = data.episodes[currentIndex], r = record(ep);
    $("task-title").textContent = ep.original_task;
    $("episode-meta").textContent = `Episode ${ep.episode_id} · ${ep.source_split} · ${ep.frame_count} frames @ ${ep.fps.toFixed(2)} fps · ${ep.segmentation_status}`;
    video.src = ep.video_url || ""; video.load();
    $("video-error").hidden = Boolean(ep.video_url);
    $("video-error").textContent = ep.video_url ? "" : "No uploaded video URL for this episode.";
    document.querySelectorAll(".episode-button").forEach(button => {
      const active = Number(button.dataset.index) === currentIndex; button.classList.toggle("active", active);
      if (active) button.closest("details").open = true;
      const item = data.episodes[Number(button.dataset.index)]; button.classList.toggle("reviewed", Boolean(state[episodeKey(item)]?.reviewed));
    });
    $("mark-reviewed").textContent = r.reviewed ? "Reviewed ✓" : "Mark reviewed";
    renderTimeline(); renderEditor(); updateFrameReadout();
  }

  function updateFrameReadout() { const ep = data.episodes[currentIndex]; $("frame-readout").textContent = `frame ${frameNow(ep)} / ${ep.frame_count - 1}`; }
  function updatePlayhead() { const ep = data.episodes[currentIndex]; $("playhead").style.left = `${pct(frameNow(ep), ep)}%`; updateFrameReadout(); }
  function updateBoundaryText() { $("selected-boundary").textContent = selectedBoundary == null ? "No boundary selected" : `Boundary S${selectedBoundary + 1} → S${selectedBoundary + 2}`; }
  function updateProgress() { const reviewed = data.episodes.filter(ep => state[episodeKey(ep)]?.reviewed).length; $("progress").textContent = `${reviewed} / ${data.episodes.length} reviewed`; }

  function setBoundaryAtCurrent() {
    if (selectedBoundary == null) return;
    const ep = data.episodes[currentIndex], r = record(ep), frame = frameNow(ep), left = r.segments[selectedBoundary], right = r.segments[selectedBoundary + 1];
    if (frame < left.start_frame || frame >= right.end_frame) return;
    left.end_frame = frame; right.start_frame = frame + 1; touch(ep); renderTimeline(); renderEditor();
  }
  function splitCurrent() {
    const ep = data.episodes[currentIndex], r = record(ep), frame = frameNow(ep), s = r.segments[selectedSegment];
    if (!s || frame < s.start_frame || frame >= s.end_frame) return;
    const right = { subtask: s.subtask, start_frame: frame + 1, end_frame: s.end_frame }; s.end_frame = frame; r.segments.splice(selectedSegment + 1, 0, right); normalizeSegments(ep, r.segments); selectedBoundary = selectedSegment; touch(ep); renderTimeline(); renderEditor();
  }
  function deleteCurrent() {
    const ep = data.episodes[currentIndex], r = record(ep); if (r.segments.length <= 1) return;
    const index = selectedSegment; r.segments.splice(index, 1); normalizeSegments(ep, r.segments); selectedSegment = Math.min(index, r.segments.length - 1); selectedBoundary = null; touch(ep); renderTimeline(); renderEditor();
  }
  function resetCurrent() { const ep = data.episodes[currentIndex]; state[episodeKey(ep)] = { reviewed: false, segments: baseSegments(ep), updated_at: new Date().toISOString() }; persist(); selectEpisode(currentIndex); }

  function exportJson() {
    const payload = {
      schema_version: 1,
      exported_at_utc: new Date().toISOString(),
      frame_semantics: "inclusive continuous front-view frame indices",
      episodes: data.episodes.map(ep => {
        const r = record(ep); return { dataset: ep.dataset, task_id: ep.task_id, episode_id: ep.episode_id, episode_key: ep.episode_key, original_task: ep.original_task, video_url: ep.video_url, total_frames: ep.frame_count, fps: ep.fps, reviewed: r.reviewed, updated_at: r.updated_at, subtasks: r.segments };
      })
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `panda_subtask_review_${new Date().toISOString().replace(/[:.]/g, "-")}.json`; a.click(); URL.revokeObjectURL(url);
  }
  function importJson(file) {
    const reader = new FileReader(); reader.onload = () => {
      try {
        const payload = JSON.parse(reader.result); (payload.episodes || []).forEach(item => {
          const ep = data.episodes.find(value => value.task_id === item.task_id && value.episode_id === item.episode_id); if (!ep || !Array.isArray(item.subtasks)) return;
          const segments = clone(item.subtasks); normalizeSegments(ep, segments); state[episodeKey(ep)] = { reviewed: Boolean(item.reviewed), updated_at: item.updated_at || new Date().toISOString(), segments };
        }); persist(); selectEpisode(currentIndex);
      } catch (error) { alert(`Import failed: ${error.message}`); }
    }; reader.readAsText(file);
  }

  timeline.addEventListener("click", event => { if (event.target.closest(".boundary-handle,.segment-block")) return; const ep = data.episodes[currentIndex], rect = timeline.getBoundingClientRect(); seekFrame(ep, Math.round((event.clientX - rect.left) / rect.width * (ep.frame_count - 1))); });
  document.addEventListener("pointermove", event => {
    if (!draggingBoundary || event.pointerId !== draggingBoundary.pointerId) return;
    event.preventDefault();
    moveBoundaryFromPointer(event.clientX);
  }, { passive: false });
  document.addEventListener("pointerup", finishBoundaryDrag);
  document.addEventListener("pointercancel", finishBoundaryDrag);
  video.addEventListener("timeupdate", updatePlayhead); video.addEventListener("seeked", updatePlayhead); video.addEventListener("error", () => { $("video-error").hidden = false; $("video-error").textContent = "Video could not be loaded. Check RustFS public/download access and object URL."; });
  $("prev-episode").onclick = () => selectEpisode(currentIndex - 1); $("next-episode").onclick = () => selectEpisode(currentIndex + 1);
  $("step-back").onclick = () => seekFrame(data.episodes[currentIndex], frameNow(data.episodes[currentIndex]) - 1); $("step-forward").onclick = () => seekFrame(data.episodes[currentIndex], frameNow(data.episodes[currentIndex]) + 1);
  $("set-boundary").onclick = setBoundaryAtCurrent; $("split-segment").onclick = splitCurrent; $("delete-segment").onclick = deleteCurrent; $("reset-episode").onclick = resetCurrent;
  $("mark-reviewed").onclick = () => { const ep = data.episodes[currentIndex], r = record(ep); r.reviewed = !r.reviewed; r.updated_at = new Date().toISOString(); persist(); selectEpisode(currentIndex); };
  $("export-json").onclick = exportJson; $("import-json").onclick = () => $("import-file").click(); $("import-file").onchange = event => event.target.files[0] && importJson(event.target.files[0]);
  document.addEventListener("keydown", event => {
    if (event.target.matches("input")) return;
    const ep = data.episodes[currentIndex];
    if (event.key === " ") { event.preventDefault(); video.paused ? video.play() : video.pause(); }
    else if (event.key === "n" || event.key === "ArrowDown") selectEpisode(currentIndex + 1);
    else if (event.key === "p" || event.key === "ArrowUp") selectEpisode(currentIndex - 1);
    else if (event.key === ",") seekFrame(ep, frameNow(ep) - 1);
    else if (event.key === ".") seekFrame(ep, frameNow(ep) + 1);
    else if (event.key === "[") { const count = record(ep).segments.length - 1; selectedBoundary = Math.max(0, (selectedBoundary ?? 1) - 1); if (count > 0) { renderTimeline(); updateBoundaryText(); } }
    else if (event.key === "]") { const count = record(ep).segments.length - 1; selectedBoundary = Math.min(count - 1, (selectedBoundary ?? -1) + 1); if (count > 0) { renderTimeline(); updateBoundaryText(); } }
    else if (event.key.toLowerCase() === "b") setBoundaryAtCurrent();
    else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); const r = record(ep); r.reviewed = true; r.updated_at = new Date().toISOString(); persist(); selectEpisode(currentIndex); }
    else if (event.key.toLowerCase() === "e") exportJson();
  });

  renderDirectory(); renderLabels(); updateProgress(); selectEpisode(0);
})();

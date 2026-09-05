(() => {
  "use strict";

  const data = window.INTENTION_REVIEW_DATA;
  if (!data || !Array.isArray(data.episodes)) throw new Error("Missing data.js");

  const $ = id => document.getElementById(id);
  const video = $("video");
  const missionColors = ["#177fc9", "#2b9c88", "#cc7b26", "#a34d72", "#4d78c8", "#698d42", "#9a58b5"];
  const longColors = ["#25a986", "#287fae", "#699d42", "#a26938"];
  const atomicColors = ["#7257d5", "#9270d8", "#5d6fc4", "#8062a8", "#555ec2", "#9266b4", "#626bb0"];
  const reviewedStorageKey = "panda-eval-6062-v2-reviewed-v1";
  const serverReviewed = new Set(data.episodes.filter(ep => ep.reviewed).map(ep => ep.parent_episode_key));
  const reviewed = new Set([
    ...serverReviewed,
    ...JSON.parse(localStorage.getItem(reviewedStorageKey) || "[]"),
  ]);
  const directoryButtons = new Map();
  let currentIndex = 0;
  let currentRecord = null;
  let selectedLane = "mission";
  let selectedIndex = 0;
  let selectedBoundary = null;
  let dragging = null;
  let draggingPlayhead = null;
  let currentFilter = "all";
  let selectionToken = 0;
  let pendingPreviewFrame = null;
  let previewAnimation = null;
  let idCounter = 0;
  let currentView = "front";

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function episodeKey(ep) { return ep.parent_episode_key; }
  function newId(prefix) { idCounter += 1; return `${prefix}_${Date.now().toString(36)}_${idCounter}`; }
  function framePct(frame, ep) { return 100 * frame / Math.max(1, ep.total_frames - 1); }
  function intervalLeft(frame, ep) { return 100 * frame / ep.total_frames; }
  function intervalWidth(start, end, ep) { return 100 * (end - start + 1) / ep.total_frames; }

  function playableVideoUrl(ep, view = currentView) {
    return ep.video_urls?.[view] || ep.video_url;
  }

  const databasePromise = new Promise((resolve, reject) => {
    const request = indexedDB.open("panda-eval-6062-review-v2", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("records", { keyPath: "parent_episode_key" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

  async function dbGet(key) {
    const db = await databasePromise;
    return new Promise((resolve, reject) => {
      const request = db.transaction("records", "readonly").objectStore("records").get(key);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  async function dbGetAll() {
    const db = await databasePromise;
    return new Promise((resolve, reject) => {
      const request = db.transaction("records", "readonly").objectStore("records").getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  async function dbPut(record) {
    const db = await databasePromise;
    return new Promise((resolve, reject) => {
      const request = db.transaction("records", "readwrite").objectStore("records").put(clone(record));
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async function dbDelete(key) {
    const db = await databasePromise;
    return new Promise((resolve, reject) => {
      const request = db.transaction("records", "readwrite").objectStore("records").delete(key);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async function dbPutMany(records) {
    const db = await databasePromise;
    return new Promise((resolve, reject) => {
      const transaction = db.transaction("records", "readwrite");
      const store = transaction.objectStore("records");
      records.forEach(record => store.put(record));
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  function baseRecord(ep) {
    const missions = clone(ep.short_term_missions || ep.missions);
    return {
      parent_episode_key: episodeKey(ep),
      full_episode_instruction: ep.full_episode_instruction,
      atomic_tasks: clone(ep.atomic_tasks),
      missions,
      long_horizon: Boolean(ep.long_horizon),
      long_term_missions: clone(ep.long_term_missions || []),
      reviewed: false,
      updated_at: null,
      server_review_revision: ep.human_review_revision || null,
      record_schema_version: 10,
    };
  }

  function migrateRecord(stored, ep, isReviewed) {
    const serverRevision = ep.human_review_revision || null;
    if (serverRevision && (!stored || stored.server_review_revision !== serverRevision)) {
      return baseRecord(ep);
    }
    // Reviewed records are user-owned: preserve their labels and boundaries.
    // Old unreviewed records are stale pre-reanalysis cache entries and should
    // adopt the new video-derived base annotation once.
    if (!stored || (!isReviewed && Number(stored.record_schema_version || 0) < 10)) return baseRecord(ep);
    const record = clone(stored);
    if (!Array.isArray(record.missions) || !record.missions.length) {
      record.missions = clone(record.short_term_missions || ep.short_term_missions || ep.missions);
    }
    if (!Array.isArray(record.atomic_tasks) || !record.atomic_tasks.length) record.atomic_tasks = clone(ep.atomic_tasks);
    if (!("long_horizon" in record)) record.long_horizon = isReviewed ? false : Boolean(ep.long_horizon);
    if (!Array.isArray(record.long_term_missions)) record.long_term_missions = isReviewed ? [] : clone(ep.long_term_missions || []);
    if (!("server_review_revision" in record)) record.server_review_revision = serverRevision;
    record.record_schema_version = 10;
    return record;
  }

  function saveReviewedIndex() {
    localStorage.setItem(reviewedStorageKey, JSON.stringify([...reviewed]));
    updateSummary();
  }

  async function persistCurrent() {
    if (!currentRecord) return;
    syncMissionMembership(currentRecord);
    syncLongTermDefinitions(currentRecord);
    currentRecord.updated_at = new Date().toISOString();
    $("save-status").textContent = "Saving…";
    $("save-status").classList.add("saving");
    await dbPut(currentRecord);
    $("save-status").textContent = "Saved locally";
    $("save-status").classList.remove("saving");
  }

  function atomicsOverlappingMission(mission, record = currentRecord) {
    return record.atomic_tasks.filter(atomic =>
      atomic.end_frame >= mission.start_frame && atomic.start_frame <= mission.end_frame
    );
  }

  function syncMissionMembership(record = currentRecord) {
    record.missions.forEach(mission => {
      mission.short_term_mission_id = mission.short_term_mission_id || mission.mission_id;
      mission.short_term_mission = mission.mission;
      mission.atomic_task_ids = atomicsOverlappingMission(mission, record).map(atomic => atomic.atomic_task_id);
    });
  }

  function syncLongTermDefinitions(record = currentRecord) {
    if (!record.long_horizon) return;
    const indexed = new Map(record.missions.map(mission => [mission.mission_id, mission]));
    record.long_term_missions.forEach((longMission, index) => {
      longMission.long_term_mission_id = longMission.long_term_mission_id || `long_term_mission_${index + 1}`;
      const memberIds = (longMission.member_short_term_mission_ids || []).filter(id => indexed.has(id));
      longMission.member_short_term_mission_ids = memberIds;
      const members = memberIds.map(id => indexed.get(id)).sort((a, b) => a.start_frame - b.start_frame);
      if (!members.length) return;
      longMission.start_frame = members[0].start_frame;
      longMission.end_frame = members[members.length - 1].end_frame;
      const activationPosition = Math.min(3, members.length);
      const activation = members[activationPosition - 1];
      longMission.activation_member_position = activationPosition;
      longMission.activation_short_term_mission_id = activation.mission_id;
      longMission.activation_frame = activation.start_frame;
    });
  }

  function laneSegments(lane) {
    if (lane === "long") return currentRecord.long_term_missions;
    return lane === "mission" ? currentRecord.missions : currentRecord.atomic_tasks;
  }

  function segmentLabel(lane, segment) {
    if (lane === "long") return segment.long_term_mission;
    return lane === "mission" ? segment.mission : segment.atomic_task;
  }

  function lanePrefix(lane) { return lane === "long" ? "L" : lane === "mission" ? "M" : "A"; }

  function normalizeAtomic(ep) {
    const atoms = currentRecord.atomic_tasks;
    atoms.sort((a, b) => a.start_frame - b.start_frame);
    atoms[0].start_frame = 0;
    for (let index = 1; index < atoms.length; index++) atoms[index].start_frame = atoms[index - 1].end_frame + 1;
    atoms[atoms.length - 1].end_frame = ep.total_frames - 1;
  }

  function frameNow(ep) {
    return Math.max(0, Math.min(ep.total_frames - 1, Math.round(video.currentTime * ep.fps)));
  }

  function seekFrame(ep, frame) {
    const target = Math.max(0, Math.min(ep.total_frames - 1, Number(frame)));
    video.currentTime = target / ep.fps;
    updatePlayheads(target);
  }

  function previewFrame(ep, frame) {
    pendingPreviewFrame = Math.max(0, Math.min(ep.total_frames - 1, Number(frame)));
    updatePlayheads(pendingPreviewFrame);
    if (previewAnimation !== null) return;
    previewAnimation = requestAnimationFrame(() => {
      const target = pendingPreviewFrame;
      pendingPreviewFrame = null;
      previewAnimation = null;
      if (target !== null) video.currentTime = target / ep.fps;
    });
  }

  function updatePlayheads(frame = null) {
    const ep = data.episodes[currentIndex];
    const value = frame === null ? frameNow(ep) : frame;
    document.querySelectorAll(".playhead").forEach(item => item.style.left = `${framePct(value, ep)}%`);
    $("frame-readout").textContent = `frame ${value} / ${ep.total_frames - 1}`;
  }

  function renderDirectory() {
    const groups = new Map();
    data.episodes.forEach((ep, index) => {
      const groupLabel = ep.task_label || ep.dataset_label;
      if (!groups.has(groupLabel)) groups.set(groupLabel, []);
      groups.get(groupLabel).push({ ep, index });
    });
    const root = $("episode-directory");
    root.textContent = "";
    groups.forEach((items, label) => {
      const details = document.createElement("details");
      details.className = "dataset-group";
      const summary = document.createElement("summary");
      const title = document.createElement("span"); title.textContent = label;
      const count = document.createElement("span"); count.className = "dataset-count"; count.textContent = `${items.length} episodes`;
      summary.append(title, count); details.appendChild(summary);
      items.forEach(({ ep, index }) => {
        const button = document.createElement("button");
        button.className = "episode-button";
        button.dataset.index = index;
        button.dataset.search = `${ep.dataset_label} ${ep.task_label || ""} ${ep.task_id} ${ep.episode_id} ${ep.episode_name || ""} ${ep.full_episode_instruction}`.toLowerCase();
        const dot = document.createElement("span"); dot.className = "status-dot";
        const text = document.createElement("span"); text.className = "episode-main";
        const name = document.createElement("span"); name.className = "episode-name"; name.textContent = `Episode ${ep.episode_id} · ${ep.episode_name || `Task ${ep.task_id}`}`;
        const instruction = document.createElement("span"); instruction.className = "episode-instruction"; instruction.textContent = ep.full_episode_instruction;
        text.append(name, instruction);
        const split = document.createElement("span"); split.className = "episode-split"; split.textContent = ep.split || "";
        button.append(dot, text, split);
        button.addEventListener("click", () => selectEpisode(index));
        details.appendChild(button);
        directoryButtons.set(index, button);
      });
      root.appendChild(details);
    });
    applyDirectoryFilter();
  }

  function applyDirectoryFilter() {
    const query = $("episode-search").value.trim().toLowerCase();
    document.querySelectorAll(".dataset-group").forEach(group => {
      let visible = 0;
      group.querySelectorAll(".episode-button").forEach(button => {
        const key = episodeKey(data.episodes[Number(button.dataset.index)]);
        const matchesState = currentFilter === "all" || (currentFilter === "reviewed" ? reviewed.has(key) : !reviewed.has(key));
        const matchesQuery = !query || button.dataset.search.includes(query);
        button.hidden = !(matchesState && matchesQuery);
        if (!button.hidden) visible += 1;
      });
      group.hidden = visible === 0;
      if (query && visible) group.open = true;
    });
  }

  function updateDirectoryActive() {
    directoryButtons.forEach((button, index) => {
      const key = episodeKey(data.episodes[index]);
      button.classList.toggle("active", index === currentIndex);
      button.classList.toggle("reviewed", reviewed.has(key));
      if (index === currentIndex) button.closest("details").open = true;
    });
  }

  function makeBlock(lane, segment, index, ep) {
    const block = document.createElement("div");
    const boundarySource = String(segment.boundary_source || "");
    const inferred = lane === "atomic" && (boundarySource.includes("unverified") || boundarySource.includes("requires_review"));
    block.className = `segment-block ${selectedLane === lane && selectedIndex === index ? "selected" : ""} ${inferred ? "inferred" : ""}`;
    block.style.left = `${intervalLeft(segment.start_frame, ep)}%`;
    block.style.width = `${intervalWidth(segment.start_frame, segment.end_frame, ep)}%`;
    const colors = lane === "long" ? longColors : lane === "mission" ? missionColors : atomicColors;
    block.style.background = colors[index % colors.length];
    const label = document.createElement("span");
    label.textContent = `${lanePrefix(lane)}${index + 1}. ${segmentLabel(lane, segment)}`;
    block.appendChild(label);
    block.title = label.textContent;
    block.addEventListener("click", event => {
      event.stopPropagation();
      selectedLane = lane; selectedIndex = index; selectedBoundary = null;
      video.pause(); previewFrame(ep, segment.start_frame); renderAll();
    });
    return block;
  }

  function makeBoundary(lane, index, frame, ep, inferred = false) {
    const handle = document.createElement("div");
    handle.className = `boundary-handle ${inferred ? "inferred" : ""} ${selectedBoundary?.lane === lane && selectedBoundary.index === index ? "selected" : ""}`;
    handle.style.left = `${100 * (frame + 1) / ep.total_frames}%`;
    handle.dataset.lane = lane; handle.dataset.index = index;
    handle.addEventListener("pointerdown", event => {
      event.preventDefault(); event.stopPropagation(); video.pause();
      selectedLane = lane; selectedIndex = index; selectedBoundary = { lane, index };
      dragging = { lane, index, pointerId: event.pointerId };
      handle.setPointerCapture(event.pointerId);
      previewFrame(ep, frame); renderSelectionStatus();
    });
    return handle;
  }

  function renderTimelines() {
    const ep = data.episodes[currentIndex];
    const longLane = $("long-mission-lane");
    longLane.hidden = !currentRecord.long_horizon;
    const longTrack = $("long-mission-track"); longTrack.textContent = "";
    if (currentRecord.long_horizon) {
      currentRecord.long_term_missions.forEach((mission, index) => {
        longTrack.appendChild(makeBlock("long", mission, index, ep));
      });
    }
    const missionTrack = $("mission-track"); missionTrack.textContent = "";
    currentRecord.missions.forEach((mission, index) => {
      missionTrack.appendChild(makeBlock("mission", mission, index, ep));
      if (index < currentRecord.missions.length - 1) missionTrack.appendChild(makeBoundary("mission", index, mission.end_frame, ep));
    });
    const atomicTrack = $("atomic-track"); atomicTrack.textContent = "";
    currentRecord.atomic_tasks.forEach((atomic, index) => {
      atomicTrack.appendChild(makeBlock("atomic", atomic, index, ep));
      if (index < currentRecord.atomic_tasks.length - 1) {
        const inferred = atomic.boundary_source === "uniform_within_mission_requires_review";
        atomicTrack.appendChild(makeBoundary("atomic", index, atomic.end_frame, ep, inferred));
      }
    });
    $("last-frame-label").textContent = ep.total_frames - 1;
    updatePlayheads();
  }

  function selectFromEditor(lane, index, seek = false) {
    selectedLane = lane; selectedIndex = index; selectedBoundary = null;
    if (seek) {
      const ep = data.episodes[currentIndex];
      const segment = laneSegments(lane)[index];
      previewFrame(ep, segment.start_frame);
    }
    renderAll();
  }

  function renderEditors() {
    const longPanel = $("long-editor-panel");
    longPanel.hidden = !currentRecord.long_horizon;
    const longRoot = $("long-editor"); longRoot.textContent = "";
    if (currentRecord.long_horizon) {
      currentRecord.long_term_missions.forEach((mission, index) => {
        const row = document.createElement("div"); row.className = `editor-row ${selectedLane === "long" && selectedIndex === index ? "selected" : ""}`; row.style.setProperty("--row-color", longColors[index % longColors.length]);
        const main = document.createElement("div"); main.className = "editor-row-main";
        const number = document.createElement("span"); number.className = "editor-index"; number.textContent = `L${index + 1}`;
        const input = document.createElement("input"); input.className = "editor-label"; input.value = mission.long_term_mission; input.setAttribute("aria-label", `Long-term mission ${index + 1}`);
        input.addEventListener("change", async () => { mission.long_term_mission = input.value.trim() || mission.long_term_mission; await persistCurrent(); renderTimelines(); });
        const range = document.createElement("span"); range.className = "editor-range"; range.textContent = `${mission.start_frame}–${mission.end_frame}`;
        main.append(number, input, range); row.appendChild(main);
        const chips = document.createElement("div"); chips.className = "atomic-chips";
        const members = new Map(currentRecord.missions.map(item => [item.mission_id, item]));
        (mission.member_short_term_mission_ids || []).forEach(id => {
          const member = members.get(id); if (!member) return;
          const chip = document.createElement("span"); chip.className = "atomic-chip"; chip.textContent = member.mission; chips.appendChild(chip);
        });
        row.appendChild(chips);
        const note = document.createElement("div"); note.className = "source-note"; note.textContent = `Prediction activates at frame ${mission.activation_frame} (third member short-term mission)`; row.appendChild(note);
        row.addEventListener("click", event => { if (event.target !== input) selectFromEditor("long", index, true); });
        longRoot.appendChild(row);
      });
    }
    const missionRoot = $("mission-editor"); missionRoot.textContent = "";
    currentRecord.missions.forEach((mission, index) => {
      const row = document.createElement("div"); row.className = `editor-row ${selectedLane === "mission" && selectedIndex === index ? "selected" : ""}`; row.style.setProperty("--row-color", missionColors[index % 7]);
      const main = document.createElement("div"); main.className = "editor-row-main";
      const number = document.createElement("span"); number.className = "editor-index"; number.textContent = `M${index + 1}`;
      const input = document.createElement("input"); input.className = "editor-label"; input.value = mission.mission; input.setAttribute("aria-label", `Mission ${index + 1}`);
      input.addEventListener("change", async () => { mission.mission = input.value.trim() || mission.mission; await persistCurrent(); renderTimelines(); });
      const range = document.createElement("span"); range.className = "editor-range"; range.textContent = `${mission.start_frame}–${mission.end_frame}`;
      main.append(number, input, range); row.appendChild(main);
      const chips = document.createElement("div"); chips.className = "atomic-chips";
      atomicsOverlappingMission(mission).forEach(atomic => { const chip = document.createElement("span"); chip.className = "atomic-chip"; chip.textContent = atomic.atomic_task; chips.appendChild(chip); });
      row.appendChild(chips);
      row.addEventListener("click", event => { if (event.target !== input) selectFromEditor("mission", index, true); });
      missionRoot.appendChild(row);
    });

    const atomicRoot = $("atomic-editor"); atomicRoot.textContent = "";
    currentRecord.atomic_tasks.forEach((atomic, index) => {
      const row = document.createElement("div"); row.className = `editor-row ${selectedLane === "atomic" && selectedIndex === index ? "selected" : ""}`; row.style.setProperty("--row-color", atomicColors[index % 7]);
      const main = document.createElement("div"); main.className = "editor-row-main";
      const number = document.createElement("span"); number.className = "editor-index"; number.textContent = `A${index + 1}`;
      const input = document.createElement("input"); input.className = "editor-label"; input.value = atomic.atomic_task; input.setAttribute("aria-label", `Atomic task ${index + 1}`);
      input.addEventListener("change", async () => { atomic.atomic_task = input.value.trim() || atomic.atomic_task; await persistCurrent(); renderTimelines(); renderEditors(); });
      const range = document.createElement("span"); range.className = "editor-range"; range.textContent = `${atomic.start_frame}–${atomic.end_frame}`;
      main.append(number, input, range); row.appendChild(main);
      if (atomic.boundary_source === "uniform_within_mission_requires_review") {
        const note = document.createElement("div"); note.className = "source-note"; note.textContent = "Internal boundary initialized uniformly — verify by video"; row.appendChild(note);
      }
      row.addEventListener("click", event => { if (event.target !== input) selectFromEditor("atomic", index, true); });
      atomicRoot.appendChild(row);
    });
    $("long-count").textContent = `${currentRecord.long_term_missions.length} total`;
    $("mission-count").textContent = `${currentRecord.missions.length} total`;
    $("atomic-count").textContent = `${currentRecord.atomic_tasks.length} total`;
  }

  function renderSelectionStatus() {
    const lane = selectedLane;
    const values = laneSegments(lane);
    if (!values.length) { selectedLane = "mission"; selectedIndex = 0; return renderSelectionStatus(); }
    selectedIndex = Math.max(0, Math.min(values.length - 1, selectedIndex));
    const segment = values[selectedIndex];
    const title = lane === "long" ? "Long-term mission L" : lane === "mission" ? "Short-term mission M" : "Atomic task A";
    $("selection-title").textContent = `${title}${selectedIndex + 1}`;
    $("selection-range").textContent = `frames ${segment.start_frame}–${segment.end_frame}`;
    $("mission-tools").hidden = lane !== "mission";
    $("atomic-tools").hidden = lane !== "atomic";
    $("long-tools").hidden = lane !== "long";
    $("merge-mission").disabled = lane !== "mission" || selectedIndex >= currentRecord.missions.length - 1;
    $("merge-atomic").disabled = lane !== "atomic" || selectedIndex >= currentRecord.atomic_tasks.length - 1;
    $("set-boundary").disabled = !selectedBoundary;
  }

  function renderAll() {
    renderTimelines(); renderEditors(); renderSelectionStatus();
  }

  function updateViewToggle(ep) {
    document.querySelectorAll(".view-button").forEach(button => {
      const available = Boolean(ep.video_urls?.[button.dataset.view] || (button.dataset.view === "front" && ep.video_url));
      button.disabled = !available;
      button.classList.toggle("active", button.dataset.view === currentView);
    });
  }

  function selectView(view) {
    const ep = data.episodes[currentIndex];
    if (view === currentView || !playableVideoUrl(ep, view)) return;
    const frame = frameNow(ep);
    video.pause(); currentView = view; updateViewToggle(ep);
    video.src = playableVideoUrl(ep, view); video.load();
    video.addEventListener("loadedmetadata", () => seekFrame(ep, frame), { once: true });
  }

  async function selectEpisode(index) {
    const token = ++selectionToken;
    currentIndex = Math.max(0, Math.min(data.episodes.length - 1, index));
    const ep = data.episodes[currentIndex];
    const stored = await dbGet(episodeKey(ep));
    if (token !== selectionToken) return;
    const isReviewed = reviewed.has(episodeKey(ep));
    currentRecord = migrateRecord(stored, ep, isReviewed);
    currentRecord.reviewed = isReviewed;
    syncMissionMembership(currentRecord); syncLongTermDefinitions(currentRecord);
    selectedLane = "mission"; selectedIndex = 0; selectedBoundary = null;
    currentView = "front";
    $("episode-kicker").textContent = `${ep.dataset_label} · Episode ${ep.episode_id} · Task ${ep.task_id}`;
    $("full-instruction").value = currentRecord.full_episode_instruction;
    $("episode-meta").textContent = `${ep.split || ""} · ${ep.total_frames} frames @ ${ep.fps.toFixed(3)} fps · ${currentRecord.missions.length} short missions · ${currentRecord.long_term_missions.length} long missions · ${currentRecord.atomic_tasks.length} atomic tasks`;
    $("long-horizon").checked = currentRecord.long_horizon;
    video.src = playableVideoUrl(ep); video.load(); updateViewToggle(ep);
    $("video-error").hidden = true;
    $("mark-reviewed").textContent = currentRecord.reviewed ? "Reviewed ✓" : "Mark reviewed";
    $("mark-reviewed").classList.toggle("reviewed", currentRecord.reviewed);
    updateDirectoryActive(); renderAll(); seekFrame(ep, 0);
  }

  function moveAtomicBoundary(index, rawFrame) {
    const atoms = currentRecord.atomic_tasks;
    const left = atoms[index], right = atoms[index + 1];
    const frame = Math.max(left.start_frame, Math.min(right.end_frame - 1, rawFrame));
    left.end_frame = frame; right.start_frame = frame + 1;
    left.boundary_source = "manual_review";
    return frame;
  }

  function moveMissionBoundary(index, rawFrame) {
    const left = currentRecord.missions[index], right = currentRecord.missions[index + 1];
    const frame = Math.max(left.start_frame, Math.min(right.end_frame - 1, rawFrame));
    left.end_frame = frame; right.start_frame = frame + 1;
    return frame;
  }

  function moveBoundaryFromPointer(clientX) {
    if (!dragging) return;
    const ep = data.episodes[currentIndex];
    const timeline = dragging.lane === "mission" ? $("mission-timeline") : $("atomic-timeline");
    const rect = timeline.getBoundingClientRect();
    const raw = Math.round((clientX - rect.left) / rect.width * (ep.total_frames - 1));
    const frame = dragging.lane === "atomic" ? moveAtomicBoundary(dragging.index, raw) : moveMissionBoundary(dragging.index, raw);
    previewFrame(ep, frame); renderTimelines(); renderEditors(); renderSelectionStatus();
  }

  async function finishDrag(event) {
    if (!dragging || (event && event.pointerId !== dragging.pointerId)) return;
    dragging = null;
    await persistCurrent(); renderAll();
  }

  function movePlayheadFromPointer(clientX) {
    if (!draggingPlayhead) return;
    const ep = data.episodes[currentIndex];
    const rect = draggingPlayhead.timeline.getBoundingClientRect();
    const raw = Math.round((clientX - rect.left) / rect.width * (ep.total_frames - 1));
    previewFrame(ep, raw);
  }

  function finishPlayheadDrag(event) {
    if (!draggingPlayhead || (event && event.pointerId !== draggingPlayhead.pointerId)) return false;
    draggingPlayhead.element.classList.remove("dragging");
    draggingPlayhead = null;
    return true;
  }

  function openDialog(title, help, fields, apply) {
    const dialog = $("edit-dialog");
    $("dialog-title").textContent = title; $("dialog-help").textContent = help;
    const root = $("dialog-fields"); root.textContent = "";
    fields.forEach(field => {
      const wrap = document.createElement("div"); wrap.className = "dialog-field";
      const label = document.createElement("label"); label.htmlFor = `field-${field.id}`; label.textContent = field.label;
      const input = document.createElement("input"); input.id = `field-${field.id}`; input.name = field.id; input.value = field.value || ""; input.required = true;
      wrap.append(label, input); root.appendChild(wrap);
    });
    const form = $("edit-form");
    const handler = event => {
      if (event.submitter?.value === "cancel") return;
      event.preventDefault();
      const values = Object.fromEntries(fields.map(field => [field.id, form.elements[field.id].value.trim()]));
      if (Object.values(values).some(value => !value)) return;
      dialog.close(); apply(values);
    };
    form.addEventListener("submit", handler, { once: true });
    dialog.showModal(); setTimeout(() => form.elements[fields[0].id].select(), 0);
  }

  function mergeMission() {
    const index = selectedIndex;
    if (index >= currentRecord.missions.length - 1) return;
    const left = currentRecord.missions[index], right = currentRecord.missions[index + 1];
    openDialog("Merge two missions", "Only the mission track changes. Atomic tasks and their boundaries stay unchanged.", [
      { id: "mission", label: "Merged mission", value: `${left.mission}; ${right.mission}` },
    ], async values => {
      left.mission = values.mission; left.end_frame = right.end_frame;
      currentRecord.missions.splice(index + 1, 1); selectedBoundary = null;
      await persistCurrent(); renderAll();
    });
  }

  function splitMission() {
    const ep = data.episodes[currentIndex], mission = currentRecord.missions[selectedIndex], frame = frameNow(ep);
    if (frame < mission.start_frame || frame >= mission.end_frame) return alert("Move the video to a frame inside the selected mission, before its final frame.");
    const fields = [
      { id: "left_mission", label: "First mission", value: mission.mission },
      { id: "right_mission", label: "Second mission", value: mission.mission },
    ];
    openDialog("Split mission at current frame", `Create two missions at frame ${frame}. Atomic tasks stay unchanged.`, fields, async values => {
      const rightMission = { mission_id: newId("mission"), mission: values.right_mission, start_frame: frame + 1, end_frame: mission.end_frame, atomic_task_ids: [] };
      mission.mission = values.left_mission; mission.end_frame = frame;
      currentRecord.missions.splice(selectedIndex + 1, 0, rightMission);
      selectedBoundary = { lane: "mission", index: selectedIndex };
      await persistCurrent(); renderAll();
    });
  }

  function splitAtomic() {
    const ep = data.episodes[currentIndex], atom = currentRecord.atomic_tasks[selectedIndex], frame = frameNow(ep);
    if (frame < atom.start_frame || frame >= atom.end_frame) return alert("Move the video to a frame inside the selected atomic task, before its final frame.");
    openDialog("Split atomic task", `Create two atomic tasks at frame ${frame}. Missions stay unchanged.`, [
      { id: "left", label: "Atomic task before boundary", value: atom.atomic_task },
      { id: "right", label: "Atomic task after boundary", value: atom.atomic_task },
    ], async values => {
      const right = { ...atom, atomic_task_id: newId("atomic"), atomic_task: values.right, start_frame: frame + 1, end_frame: atom.end_frame, boundary_source: "manual_review" };
      atom.atomic_task = values.left; atom.end_frame = frame; atom.boundary_source = "manual_review";
      currentRecord.atomic_tasks.splice(selectedIndex + 1, 0, right);
      selectedBoundary = { lane: "atomic", index: selectedIndex };
      await persistCurrent(); renderAll();
    });
  }

  function mergeAtomic() {
    const index = selectedIndex;
    if (index >= currentRecord.atomic_tasks.length - 1) return;
    const left = currentRecord.atomic_tasks[index], right = currentRecord.atomic_tasks[index + 1];
    openDialog("Merge two atomic tasks", "Only the atomic track changes. Missions and their boundaries stay unchanged.", [
      { id: "atomic", label: "Merged atomic task", value: `${left.atomic_task}; ${right.atomic_task}` },
    ], async values => {
      left.atomic_task = values.atomic; left.end_frame = right.end_frame; left.boundary_source = "manual_review";
      currentRecord.atomic_tasks.splice(index + 1, 1);
      selectedBoundary = null; await persistCurrent(); renderAll();
    });
  }

  async function setBoundaryAtCurrent() {
    if (!selectedBoundary) return;
    const ep = data.episodes[currentIndex], raw = frameNow(ep);
    const frame = selectedBoundary.lane === "atomic" ? moveAtomicBoundary(selectedBoundary.index, raw) : moveMissionBoundary(selectedBoundary.index, raw);
    seekFrame(ep, frame); await persistCurrent(); renderAll();
  }

  async function resetEpisode() {
    if (!confirm("Reset this episode to the original pre-annotation?")) return;
    const ep = data.episodes[currentIndex]; await dbDelete(episodeKey(ep));
    ep.reviewed ? reviewed.add(episodeKey(ep)) : reviewed.delete(episodeKey(ep));
    saveReviewedIndex(); await selectEpisode(currentIndex);
  }

  async function toggleReviewed() {
    const ep = data.episodes[currentIndex], key = episodeKey(ep);
    currentRecord.reviewed = !currentRecord.reviewed;
    currentRecord.reviewed ? reviewed.add(key) : reviewed.delete(key);
    saveReviewedIndex(); await persistCurrent(); updateDirectoryActive();
    $("mark-reviewed").textContent = currentRecord.reviewed ? "Reviewed ✓" : "Mark reviewed";
    $("mark-reviewed").classList.toggle("reviewed", currentRecord.reviewed);
  }

  function transferLikeMission(mission) {
    return /^(put|place|move|take|remove|transfer|store|insert|load|unload)\b/i.test(mission.mission.trim());
  }

  async function toggleLongHorizon(event) {
    const enabled = Boolean(event.target.checked);
    if (enabled && currentRecord.missions.length < 3) {
      event.target.checked = false;
      return alert("A long-horizon mission requires at least three repeated short-term missions.");
    }
    currentRecord.long_horizon = enabled;
    if (enabled && !currentRecord.long_term_missions.length) {
      let members = currentRecord.missions.filter(transferLikeMission);
      if (members.length < 3) members = currentRecord.missions.slice();
      const third = members[2];
      currentRecord.long_term_missions = [{
        long_term_mission_id: newId("long_term_mission"),
        long_term_mission: currentRecord.full_episode_instruction,
        start_frame: members[0].start_frame,
        end_frame: members[members.length - 1].end_frame,
        member_short_term_mission_ids: members.map(item => item.mission_id),
        activation_member_position: 3,
        activation_short_term_mission_id: third.mission_id,
        activation_frame: third.start_frame,
      }];
    }
    selectedLane = enabled ? "long" : "mission"; selectedIndex = 0; selectedBoundary = null;
    await persistCurrent(); renderAll();
  }

  function effectiveOngoingMissions(record) {
    const output = record.missions.map(mission => ({
      short_term_mission_id: mission.mission_id,
      start_frame: mission.start_frame,
      end_frame: mission.end_frame,
      ongoing_mission: mission.mission,
      label_source: "short_term_mission",
    }));
    if (!record.long_horizon) return output;
    const byId = new Map(output.map(item => [item.short_term_mission_id, item]));
    record.long_term_missions.forEach(longMission => {
      const members = longMission.member_short_term_mission_ids || [];
      const activation = Math.max(0, Number(longMission.activation_member_position || 3) - 1);
      members.slice(activation).forEach(id => {
        const item = byId.get(id); if (!item) return;
        item.ongoing_mission = longMission.long_term_mission;
        item.label_source = "long_term_mission";
        item.long_term_mission_id = longMission.long_term_mission_id;
      });
    });
    return output;
  }

  function exportRecord(ep, record) {
    const snapshot = clone(record);
    syncMissionMembership(snapshot);
    return {
      dataset: ep.dataset, task_id: ep.task_id, episode_id: ep.episode_id,
      parent_episode_key: ep.parent_episode_key, split: ep.split,
      full_episode_instruction: snapshot.full_episode_instruction,
      video_url: ep.video_url, video_urls: ep.video_urls, video_object_keys: ep.video_object_keys,
      record_id: ep.record_id, fps: ep.fps, total_frames: ep.total_frames,
      reviewed: Boolean(snapshot.reviewed), updated_at: snapshot.updated_at,
      atomic_tasks: snapshot.atomic_tasks,
      short_term_missions: snapshot.missions,
      missions: snapshot.missions,
      long_horizon: Boolean(snapshot.long_horizon),
      long_term_missions: snapshot.long_term_missions,
      effective_ongoing_missions: effectiveOngoingMissions(snapshot),
    };
  }

  async function exportJson() {
    const button = $("export-json"); button.disabled = true; button.textContent = "Preparing…";
    try {
      const stored = new Map((await dbGetAll()).map(record => [record.parent_episode_key, record]));
      const episodes = data.episodes.map(ep => exportRecord(ep, stored.get(episodeKey(ep)) || baseRecord(ep)));
      const payload = {
        schema_version: 5,
        exported_at_utc: new Date().toISOString(),
        hierarchy: "full episode instruction > long-term missions > short-term missions > atomic tasks",
        track_semantics: "short-term mission and atomic timelines are edited independently; long-term missions group repeated short-term missions",
        ongoing_mission_policy: "Use the short-term mission containing the sample's last observed frame. For a long-horizon group, use the long-term label from the start of its third member short-term mission onward.",
        frame_semantics: "inclusive continuous episode-local frame indices",
        episodes,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob), anchor = document.createElement("a");
      anchor.href = url; anchor.download = `panda_eval_6062_review_${new Date().toISOString().replace(/[:.]/g, "-")}.json`; anchor.click(); URL.revokeObjectURL(url);
    } finally { button.disabled = false; button.textContent = "Export JSON"; }
  }

  function validateImported(item, ep) {
    const missions = item.short_term_missions || item.missions;
    if (!Array.isArray(item.atomic_tasks) || !item.atomic_tasks.length || !Array.isArray(missions) || !missions.length) return false;
    const validTrack = segments => {
      if (Number(segments[0].start_frame) !== 0 || Number(segments[segments.length - 1].end_frame) !== ep.total_frames - 1) return false;
      return segments.every((segment, index) => Number(segment.end_frame) >= Number(segment.start_frame) && (!index || Number(segment.start_frame) === Number(segments[index - 1].end_frame) + 1));
    };
    return validTrack(item.atomic_tasks) && validTrack(missions);
  }

  function importJson(file) {
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const payload = JSON.parse(reader.result), indexed = new Map(data.episodes.map(ep => [episodeKey(ep), ep]));
        const records = [];
        for (const item of payload.episodes || []) {
          const ep = indexed.get(item.parent_episode_key); if (!ep || !validateImported(item, ep)) continue;
          records.push({
            parent_episode_key: item.parent_episode_key,
            full_episode_instruction: item.full_episode_instruction || ep.full_episode_instruction,
            atomic_tasks: clone(item.atomic_tasks), missions: clone(item.short_term_missions || item.missions),
            long_horizon: Boolean(item.long_horizon), long_term_missions: clone(item.long_term_missions || []),
            reviewed: Boolean(item.reviewed), updated_at: item.updated_at || new Date().toISOString(),
            record_schema_version: 10,
          });
          item.reviewed ? reviewed.add(item.parent_episode_key) : reviewed.delete(item.parent_episode_key);
        }
        await dbPutMany(records); saveReviewedIndex(); updateDirectoryActive(); await selectEpisode(currentIndex);
        alert(`Imported ${records.length} episode annotations.`);
      } catch (error) { alert(`Import failed: ${error.message}`); }
    };
    reader.readAsText(file);
  }

  function updateSummary() {
    $("dataset-summary").textContent = `${data.summary.episode_count.toLocaleString()} episodes · ${data.summary.video_count.toLocaleString()} videos · ${data.summary.evaluation_sample_count.toLocaleString()} eval samples · ${reviewed.size.toLocaleString()} reviewed`;
  }

  function timelineClick(event, lane) {
    if (event.target.closest(".segment-block,.boundary-handle,.playhead")) return;
    const ep = data.episodes[currentIndex], rect = event.currentTarget.getBoundingClientRect();
    seekFrame(ep, Math.round((event.clientX - rect.left) / rect.width * (ep.total_frames - 1)));
    selectedLane = lane; renderSelectionStatus();
  }

  $("mission-timeline").addEventListener("click", event => timelineClick(event, "mission"));
  $("long-mission-timeline").addEventListener("click", event => timelineClick(event, "long"));
  $("atomic-timeline").addEventListener("click", event => timelineClick(event, "atomic"));
  document.querySelectorAll(".playhead").forEach(element => {
    element.title = "Drag to preview a video frame";
    element.setAttribute("aria-label", "Current video frame; drag to seek");
    element.addEventListener("pointerdown", event => {
      event.preventDefault(); event.stopPropagation(); video.pause();
      draggingPlayhead = { element, timeline: element.closest(".timeline"), pointerId: event.pointerId };
      element.classList.add("dragging");
      element.setPointerCapture(event.pointerId);
      movePlayheadFromPointer(event.clientX);
    });
  });
  document.addEventListener("pointermove", event => {
    if (draggingPlayhead && event.pointerId === draggingPlayhead.pointerId) {
      event.preventDefault(); movePlayheadFromPointer(event.clientX); return;
    }
    if (dragging && event.pointerId === dragging.pointerId) {
      event.preventDefault(); moveBoundaryFromPointer(event.clientX);
    }
  }, { passive: false });
  document.addEventListener("pointerup", event => { if (!finishPlayheadDrag(event)) finishDrag(event); });
  document.addEventListener("pointercancel", event => { if (!finishPlayheadDrag(event)) finishDrag(event); });
  video.addEventListener("timeupdate", () => updatePlayheads()); video.addEventListener("seeked", () => updatePlayheads());
  video.addEventListener("error", () => { $("video-error").hidden = false; $("video-error").textContent = "Video could not be loaded from RustFS. This episode may still be uploading."; });
  $("full-instruction").addEventListener("change", async event => { currentRecord.full_episode_instruction = event.target.value.trim() || data.episodes[currentIndex].full_episode_instruction; await persistCurrent(); });
  $("prev-episode").onclick = () => selectEpisode(currentIndex - 1); $("next-episode").onclick = () => selectEpisode(currentIndex + 1);
  $("step-back").onclick = () => seekFrame(data.episodes[currentIndex], frameNow(data.episodes[currentIndex]) - 1);
  $("step-forward").onclick = () => seekFrame(data.episodes[currentIndex], frameNow(data.episodes[currentIndex]) + 1);
  $("mark-reviewed").onclick = toggleReviewed; $("merge-mission").onclick = mergeMission; $("split-mission").onclick = splitMission;
  $("long-horizon").addEventListener("change", toggleLongHorizon);
  $("merge-atomic").onclick = mergeAtomic; $("split-atomic").onclick = splitAtomic; $("set-boundary").onclick = setBoundaryAtCurrent;
  $("reset-episode").onclick = resetEpisode; $("export-json").onclick = exportJson;
  $("import-json").onclick = () => $("import-file").click(); $("import-file").onchange = event => event.target.files[0] && importJson(event.target.files[0]);
  $("episode-search").addEventListener("input", applyDirectoryFilter);
  document.querySelectorAll(".view-button").forEach(button => button.addEventListener("click", () => selectView(button.dataset.view)));
  document.querySelectorAll(".filter").forEach(button => button.addEventListener("click", () => {
    currentFilter = button.dataset.filter; document.querySelectorAll(".filter").forEach(item => item.classList.toggle("active", item === button)); applyDirectoryFilter();
  }));

  document.addEventListener("keydown", event => {
    if (event.target.matches("input") || $("edit-dialog").open) return;
    const ep = data.episodes[currentIndex];
    if (event.key === " ") { event.preventDefault(); video.paused ? video.play() : video.pause(); }
    else if (event.key.toLowerCase() === "n" || event.key === "ArrowDown") selectEpisode(currentIndex + 1);
    else if (event.key.toLowerCase() === "p" || event.key === "ArrowUp") selectEpisode(currentIndex - 1);
    else if (event.key === ",") seekFrame(ep, frameNow(ep) - 1);
    else if (event.key === ".") seekFrame(ep, frameNow(ep) + 1);
    else if (event.key.toLowerCase() === "b") setBoundaryAtCurrent();
    else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); if (!currentRecord.reviewed) toggleReviewed(); }
  });

  renderDirectory(); updateSummary(); selectEpisode(0);
})();

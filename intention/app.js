(() => {
  "use strict";

  const data = window.INTENTION_REVIEW_DATA;
  if (!data || !Array.isArray(data.episodes)) throw new Error("Missing data.js");

  const $ = id => document.getElementById(id);
  const video = $("video");
  const missionColors = ["#177fc9", "#2b9c88", "#cc7b26", "#a34d72", "#4d78c8", "#698d42", "#9a58b5"];
  const atomicColors = ["#7257d5", "#9270d8", "#5d6fc4", "#8062a8", "#555ec2", "#9266b4", "#626bb0"];
  const reviewedStorageKey = "intention6600-reviewed-v1";
  const reviewed = new Set(JSON.parse(localStorage.getItem(reviewedStorageKey) || "[]"));
  const directoryButtons = new Map();
  let currentIndex = 0;
  let currentRecord = null;
  let selectedLane = "mission";
  let selectedIndex = 0;
  let selectedBoundary = null;
  let dragging = null;
  let currentFilter = "all";
  let selectionToken = 0;
  let pendingPreviewFrame = null;
  let previewAnimation = null;
  let idCounter = 0;

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function episodeKey(ep) { return ep.parent_episode_key; }
  function newId(prefix) { idCounter += 1; return `${prefix}_${Date.now().toString(36)}_${idCounter}`; }
  function framePct(frame, ep) { return 100 * frame / Math.max(1, ep.total_frames - 1); }
  function intervalLeft(frame, ep) { return 100 * frame / ep.total_frames; }
  function intervalWidth(start, end, ep) { return 100 * (end - start + 1) / ep.total_frames; }

  const databasePromise = new Promise((resolve, reject) => {
    const request = indexedDB.open("intention6600-review", 1);
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
    return {
      parent_episode_key: episodeKey(ep),
      full_episode_instruction: ep.full_episode_instruction,
      atomic_tasks: clone(ep.atomic_tasks),
      missions: clone(ep.missions),
      reviewed: false,
      updated_at: null,
    };
  }

  function saveReviewedIndex() {
    localStorage.setItem(reviewedStorageKey, JSON.stringify([...reviewed]));
    updateSummary();
  }

  async function persistCurrent() {
    if (!currentRecord) return;
    currentRecord.updated_at = new Date().toISOString();
    $("save-status").textContent = "Saving…";
    $("save-status").classList.add("saving");
    await dbPut(currentRecord);
    $("save-status").textContent = "Saved locally";
    $("save-status").classList.remove("saving");
  }

  function atomicById(id) { return currentRecord.atomic_tasks.find(item => item.atomic_task_id === id); }
  function atomicIndexById(id) { return currentRecord.atomic_tasks.findIndex(item => item.atomic_task_id === id); }
  function missionRange(mission) {
    const atoms = mission.atomic_task_ids.map(atomicById).filter(Boolean);
    return { start_frame: atoms[0].start_frame, end_frame: atoms[atoms.length - 1].end_frame };
  }
  function refreshMissionRanges(record = currentRecord) {
    const index = new Map(record.atomic_tasks.map(item => [item.atomic_task_id, item]));
    record.missions.forEach(mission => {
      const atoms = mission.atomic_task_ids.map(id => index.get(id)).filter(Boolean);
      if (!atoms.length) throw new Error(`Mission ${mission.mission_id} has no atomic tasks`);
      mission.start_frame = atoms[0].start_frame;
      mission.end_frame = atoms[atoms.length - 1].end_frame;
    });
  }

  function normalizeAtomic(ep) {
    const atoms = currentRecord.atomic_tasks;
    atoms.sort((a, b) => a.start_frame - b.start_frame);
    atoms[0].start_frame = 0;
    for (let index = 1; index < atoms.length; index++) atoms[index].start_frame = atoms[index - 1].end_frame + 1;
    atoms[atoms.length - 1].end_frame = ep.total_frames - 1;
    refreshMissionRanges();
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
      if (!groups.has(ep.dataset_label)) groups.set(ep.dataset_label, []);
      groups.get(ep.dataset_label).push({ ep, index });
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
        button.dataset.search = `${ep.dataset_label} ${ep.task_id} ${ep.episode_id} ${ep.full_episode_instruction}`.toLowerCase();
        const dot = document.createElement("span"); dot.className = "status-dot";
        const text = document.createElement("span"); text.className = "episode-main";
        const name = document.createElement("span"); name.className = "episode-name"; name.textContent = `Episode ${ep.episode_id} · Task ${ep.task_id}`;
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
    const inferred = lane === "atomic" && segment.boundary_source === "uniform_within_mission_requires_review";
    block.className = `segment-block ${selectedLane === lane && selectedIndex === index ? "selected" : ""} ${inferred ? "inferred" : ""}`;
    block.style.left = `${intervalLeft(segment.start_frame, ep)}%`;
    block.style.width = `${intervalWidth(segment.start_frame, segment.end_frame, ep)}%`;
    block.style.background = (lane === "mission" ? missionColors : atomicColors)[index % 7];
    const label = document.createElement("span");
    label.textContent = `${lane === "mission" ? "M" : "A"}${index + 1}. ${lane === "mission" ? segment.mission : segment.atomic_task}`;
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
    refreshMissionRanges();
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
      const segment = lane === "mission" ? currentRecord.missions[index] : currentRecord.atomic_tasks[index];
      previewFrame(ep, segment.start_frame);
    }
    renderAll();
  }

  function renderEditors() {
    refreshMissionRanges();
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
      mission.atomic_task_ids.forEach(id => { const atomic = atomicById(id); const chip = document.createElement("span"); chip.className = "atomic-chip"; chip.textContent = atomic ? atomic.atomic_task : id; chips.appendChild(chip); });
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
    $("mission-count").textContent = `${currentRecord.missions.length} total`;
    $("atomic-count").textContent = `${currentRecord.atomic_tasks.length} total`;
  }

  function renderSelectionStatus() {
    const lane = selectedLane;
    const values = lane === "mission" ? currentRecord.missions : currentRecord.atomic_tasks;
    selectedIndex = Math.max(0, Math.min(values.length - 1, selectedIndex));
    const segment = values[selectedIndex];
    if (lane === "mission") refreshMissionRanges();
    $("selection-title").textContent = `${lane === "mission" ? "Mission M" : "Atomic task A"}${selectedIndex + 1}`;
    $("selection-range").textContent = `frames ${segment.start_frame}–${segment.end_frame}`;
    $("mission-tools").hidden = lane !== "mission";
    $("atomic-tools").hidden = lane !== "atomic";
    $("merge-mission").disabled = lane !== "mission" || selectedIndex >= currentRecord.missions.length - 1;
    $("merge-atomic").disabled = lane !== "atomic" || selectedIndex >= currentRecord.atomic_tasks.length - 1;
    $("set-boundary").disabled = !selectedBoundary;
  }

  function renderAll() {
    renderTimelines(); renderEditors(); renderSelectionStatus();
  }

  async function selectEpisode(index) {
    const token = ++selectionToken;
    currentIndex = Math.max(0, Math.min(data.episodes.length - 1, index));
    const ep = data.episodes[currentIndex];
    const stored = await dbGet(episodeKey(ep));
    if (token !== selectionToken) return;
    currentRecord = stored || baseRecord(ep);
    currentRecord.reviewed = reviewed.has(episodeKey(ep));
    selectedLane = "mission"; selectedIndex = 0; selectedBoundary = null;
    $("episode-kicker").textContent = `${ep.dataset_label} · Episode ${ep.episode_id} · Task ${ep.task_id}`;
    $("full-instruction").value = currentRecord.full_episode_instruction;
    $("episode-meta").textContent = `${ep.split || ""} · ${ep.total_frames} frames @ ${ep.fps.toFixed(3)} fps · ${currentRecord.missions.length} missions · ${currentRecord.atomic_tasks.length} atomic tasks`;
    video.src = ep.video_url; video.load();
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
    refreshMissionRanges();
    return frame;
  }

  function moveMissionBoundary(index, rawFrame) {
    const left = currentRecord.missions[index], right = currentRecord.missions[index + 1];
    const combined = [...left.atomic_task_ids, ...right.atomic_task_ids];
    const candidates = combined.slice(0, -1).map((_, cut) => ({ cut: cut + 1, frame: atomicById(combined[cut]).end_frame }));
    const choice = candidates.reduce((best, item) => Math.abs(item.frame - rawFrame) < Math.abs(best.frame - rawFrame) ? item : best);
    left.atomic_task_ids = combined.slice(0, choice.cut);
    right.atomic_task_ids = combined.slice(choice.cut);
    refreshMissionRanges();
    return choice.frame;
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

  function missionForAtomic(id) { return currentRecord.missions.find(mission => mission.atomic_task_ids.includes(id)); }

  function mergeMission() {
    const index = selectedIndex;
    if (index >= currentRecord.missions.length - 1) return;
    const left = currentRecord.missions[index], right = currentRecord.missions[index + 1];
    openDialog("Merge two missions", "The atomic tasks and frame coverage are preserved. Enter the new predictable intention.", [
      { id: "mission", label: "Merged mission", value: `${left.mission}; ${right.mission}` },
    ], async values => {
      left.mission = values.mission; left.atomic_task_ids.push(...right.atomic_task_ids);
      currentRecord.missions.splice(index + 1, 1); refreshMissionRanges(); selectedBoundary = null;
      await persistCurrent(); renderAll();
    });
  }

  function splitMission() {
    const ep = data.episodes[currentIndex], mission = currentRecord.missions[selectedIndex], frame = frameNow(ep);
    refreshMissionRanges();
    if (frame < mission.start_frame || frame >= mission.end_frame) return alert("Move the video to a frame inside the selected mission, before its final frame.");
    const atoms = mission.atomic_task_ids.map(atomicById);
    const atomPosition = atoms.findIndex(atom => frame >= atom.start_frame && frame <= atom.end_frame);
    const atom = atoms[atomPosition];
    const splitInsideAtom = frame < atom.end_frame;
    const fields = [
      { id: "left_mission", label: "First mission", value: mission.mission },
      { id: "right_mission", label: "Second mission", value: mission.mission },
    ];
    if (splitInsideAtom) fields.push(
      { id: "left_atomic", label: "Atomic task before boundary", value: atom.atomic_task },
      { id: "right_atomic", label: "Atomic task after boundary", value: atom.atomic_task },
    );
    openDialog("Split mission at current frame", `Create two missions at frame ${frame}.`, fields, async values => {
      let cut = atomPosition + 1;
      if (splitInsideAtom) {
        const rightAtom = { ...atom, atomic_task_id: newId("atomic"), atomic_task: values.right_atomic, start_frame: frame + 1, end_frame: atom.end_frame, boundary_source: "manual_review" };
        atom.atomic_task = values.left_atomic; atom.end_frame = frame; atom.boundary_source = "manual_review";
        const globalIndex = atomicIndexById(atom.atomic_task_id); currentRecord.atomic_tasks.splice(globalIndex + 1, 0, rightAtom);
        mission.atomic_task_ids.splice(atomPosition + 1, 0, rightAtom.atomic_task_id); cut = atomPosition + 1;
      }
      const rightIds = mission.atomic_task_ids.splice(cut);
      const rightMission = { mission_id: newId("mission"), mission: values.right_mission, atomic_task_ids: rightIds };
      mission.mission = values.left_mission;
      currentRecord.missions.splice(selectedIndex + 1, 0, rightMission);
      refreshMissionRanges(); selectedBoundary = { lane: "mission", index: selectedIndex };
      await persistCurrent(); renderAll();
    });
  }

  function splitAtomic() {
    const ep = data.episodes[currentIndex], atom = currentRecord.atomic_tasks[selectedIndex], frame = frameNow(ep);
    if (frame < atom.start_frame || frame >= atom.end_frame) return alert("Move the video to a frame inside the selected atomic task, before its final frame.");
    openDialog("Split atomic task", `Create two atomic tasks at frame ${frame}. They remain in the same mission.`, [
      { id: "left", label: "Atomic task before boundary", value: atom.atomic_task },
      { id: "right", label: "Atomic task after boundary", value: atom.atomic_task },
    ], async values => {
      const right = { ...atom, atomic_task_id: newId("atomic"), atomic_task: values.right, start_frame: frame + 1, end_frame: atom.end_frame, boundary_source: "manual_review" };
      atom.atomic_task = values.left; atom.end_frame = frame; atom.boundary_source = "manual_review";
      currentRecord.atomic_tasks.splice(selectedIndex + 1, 0, right);
      const mission = missionForAtomic(atom.atomic_task_id); const position = mission.atomic_task_ids.indexOf(atom.atomic_task_id);
      mission.atomic_task_ids.splice(position + 1, 0, right.atomic_task_id); refreshMissionRanges(); selectedBoundary = { lane: "atomic", index: selectedIndex };
      await persistCurrent(); renderAll();
    });
  }

  function mergeAtomic() {
    const index = selectedIndex;
    if (index >= currentRecord.atomic_tasks.length - 1) return;
    const left = currentRecord.atomic_tasks[index], right = currentRecord.atomic_tasks[index + 1];
    const leftMission = missionForAtomic(left.atomic_task_id), rightMission = missionForAtomic(right.atomic_task_id);
    if (leftMission !== rightMission) return alert("These atomic tasks belong to different missions. Merge the two missions first, then merge their atomic tasks if needed.");
    openDialog("Merge two atomic tasks", "Their frame ranges will be joined inside the current mission.", [
      { id: "atomic", label: "Merged atomic task", value: `${left.atomic_task}; ${right.atomic_task}` },
    ], async values => {
      left.atomic_task = values.atomic; left.end_frame = right.end_frame; left.boundary_source = "manual_review";
      currentRecord.atomic_tasks.splice(index + 1, 1);
      leftMission.atomic_task_ids = leftMission.atomic_task_ids.filter(id => id !== right.atomic_task_id);
      refreshMissionRanges(); selectedBoundary = null; await persistCurrent(); renderAll();
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
    const ep = data.episodes[currentIndex]; await dbDelete(episodeKey(ep)); reviewed.delete(episodeKey(ep)); saveReviewedIndex(); await selectEpisode(currentIndex);
  }

  async function toggleReviewed() {
    const ep = data.episodes[currentIndex], key = episodeKey(ep);
    currentRecord.reviewed = !currentRecord.reviewed;
    currentRecord.reviewed ? reviewed.add(key) : reviewed.delete(key);
    saveReviewedIndex(); await persistCurrent(); updateDirectoryActive();
    $("mark-reviewed").textContent = currentRecord.reviewed ? "Reviewed ✓" : "Mark reviewed";
    $("mark-reviewed").classList.toggle("reviewed", currentRecord.reviewed);
  }

  function exportRecord(ep, record) {
    refreshMissionRanges(record);
    return {
      dataset: ep.dataset, task_id: ep.task_id, episode_id: ep.episode_id,
      parent_episode_key: ep.parent_episode_key, split: ep.split,
      full_episode_instruction: record.full_episode_instruction,
      video_url: ep.video_url, fps: ep.fps, total_frames: ep.total_frames,
      reviewed: Boolean(record.reviewed), updated_at: record.updated_at,
      atomic_tasks: record.atomic_tasks,
      missions: record.missions,
    };
  }

  async function exportJson() {
    const button = $("export-json"); button.disabled = true; button.textContent = "Preparing…";
    try {
      const stored = new Map((await dbGetAll()).map(record => [record.parent_episode_key, record]));
      const episodes = data.episodes.map(ep => exportRecord(ep, stored.get(episodeKey(ep)) || baseRecord(ep)));
      const payload = {
        schema_version: 3,
        exported_at_utc: new Date().toISOString(),
        hierarchy: "full episode instruction > missions > atomic tasks",
        frame_semantics: "inclusive continuous episode-local frame indices",
        episodes,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob), anchor = document.createElement("a");
      anchor.href = url; anchor.download = `intention6600_review_${new Date().toISOString().replace(/[:.]/g, "-")}.json`; anchor.click(); URL.revokeObjectURL(url);
    } finally { button.disabled = false; button.textContent = "Export JSON"; }
  }

  function validateImported(item, ep) {
    if (!Array.isArray(item.atomic_tasks) || !item.atomic_tasks.length || !Array.isArray(item.missions) || !item.missions.length) return false;
    const atoms = item.atomic_tasks;
    if (Number(atoms[0].start_frame) !== 0 || Number(atoms[atoms.length - 1].end_frame) !== ep.total_frames - 1) return false;
    return atoms.every((atom, index) => Number(atom.end_frame) >= Number(atom.start_frame) && (!index || Number(atom.start_frame) === Number(atoms[index - 1].end_frame) + 1));
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
            atomic_tasks: clone(item.atomic_tasks), missions: clone(item.missions),
            reviewed: Boolean(item.reviewed), updated_at: item.updated_at || new Date().toISOString(),
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
    $("dataset-summary").textContent = `${data.summary.dataset_count} datasets · ${data.summary.episode_count.toLocaleString()} episodes · ${reviewed.size.toLocaleString()} reviewed`;
  }

  function timelineClick(event, lane) {
    if (event.target.closest(".segment-block,.boundary-handle")) return;
    const ep = data.episodes[currentIndex], rect = event.currentTarget.getBoundingClientRect();
    seekFrame(ep, Math.round((event.clientX - rect.left) / rect.width * (ep.total_frames - 1)));
    selectedLane = lane; renderSelectionStatus();
  }

  $("mission-timeline").addEventListener("click", event => timelineClick(event, "mission"));
  $("atomic-timeline").addEventListener("click", event => timelineClick(event, "atomic"));
  document.addEventListener("pointermove", event => { if (dragging && event.pointerId === dragging.pointerId) { event.preventDefault(); moveBoundaryFromPointer(event.clientX); } }, { passive: false });
  document.addEventListener("pointerup", finishDrag); document.addEventListener("pointercancel", finishDrag);
  video.addEventListener("timeupdate", () => updatePlayheads()); video.addEventListener("seeked", () => updatePlayheads());
  video.addEventListener("error", () => { $("video-error").hidden = false; $("video-error").textContent = "Video could not be loaded from RustFS. This episode may still be uploading."; });
  $("full-instruction").addEventListener("change", async event => { currentRecord.full_episode_instruction = event.target.value.trim() || data.episodes[currentIndex].full_episode_instruction; await persistCurrent(); });
  $("prev-episode").onclick = () => selectEpisode(currentIndex - 1); $("next-episode").onclick = () => selectEpisode(currentIndex + 1);
  $("step-back").onclick = () => seekFrame(data.episodes[currentIndex], frameNow(data.episodes[currentIndex]) - 1);
  $("step-forward").onclick = () => seekFrame(data.episodes[currentIndex], frameNow(data.episodes[currentIndex]) + 1);
  $("mark-reviewed").onclick = toggleReviewed; $("merge-mission").onclick = mergeMission; $("split-mission").onclick = splitMission;
  $("merge-atomic").onclick = mergeAtomic; $("split-atomic").onclick = splitAtomic; $("set-boundary").onclick = setBoundaryAtCurrent;
  $("reset-episode").onclick = resetEpisode; $("export-json").onclick = exportJson;
  $("import-json").onclick = () => $("import-file").click(); $("import-file").onchange = event => event.target.files[0] && importJson(event.target.files[0]);
  $("episode-search").addEventListener("input", applyDirectoryFilter);
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

(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => n.toLocaleString('en-US');
  const splitName = {train:'训练集', val:'验证集', test:'测试集', all:'全部数据'};
  const pageSize = 30, cache = new Map();
  let catalog, filtered = [], page = 0, current = null, selectedKey = '', request = 0, activeId = '', pendingFrame = null;
  const video = $('video');
  async function getJSON(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`无法读取 ${url} (HTTP ${response.status})`);
    return response.json();
  }
  function shard(dataset) {
    if (!cache.has(dataset)) {
      const meta = catalog.datasets[dataset];
      cache.set(dataset, getJSON(`${meta.url}?v=${meta.sha256.slice(0,12)}`).then(rows => new Map(rows.map(row => [row.parent_episode_key, row]))).catch(error => {cache.delete(dataset); throw error;}));
    }
    return cache.get(dataset);
  }
  function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
  function download(filename, value) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], {type:'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }
  function updateURL() {
    const url = new URL(location.href); url.search = '';
    url.searchParams.set('split', $('split').value);
    if ($('dataset').value !== 'all') url.searchParams.set('dataset', $('dataset').value);
    if ($('search').value) url.searchParams.set('q', $('search').value);
    if (selectedKey) url.searchParams.set('episode', selectedKey);
    history.replaceState(null, '', url);
  }
  function directory() {
    const maxPage = Math.max(0, Math.ceil(filtered.length / pageSize) - 1);
    page = Math.min(page, maxPage);
    const visible = filtered.slice(page * pageSize, (page + 1) * pageSize);
    $('directory').innerHTML = visible.map(row => `<button class="episode ${row.parent_episode_key === selectedKey ? 'active' : ''}" data-key="${escape(row.parent_episode_key)}" ${row.parent_episode_key === selectedKey ? 'aria-current="true"' : ''}><strong>${escape(row.dataset_label)} · ${escape(row.episode_id)}</strong><span>${escape(row.full_episode_instruction)}</span><small>${splitName[row.split]} · task ${escape(row.task_id)} · ${row.atomic_count} 动作 / ${row.mission_count} 意图</small></button>`).join('');
    $('result-count').textContent = `${fmt(filtered.length)} 条轨迹${filtered.length ? ` · 当前 ${page * pageSize + 1}–${Math.min((page + 1) * pageSize, filtered.length)}` : ''}`;
    $('page-number').textContent = `${page + 1} / ${maxPage + 1}`;
    $('page-prev').disabled = page === 0; $('page-next').disabled = page === maxPage;
    const index = filtered.findIndex(r => r.parent_episode_key === selectedKey);
    $('previous').disabled = index <= 0; $('next').disabled = index < 0 || index >= filtered.length - 1;
  }
  function filter(selectFirst = true) {
    const query = $('search').value.trim().toLowerCase();
    filtered = catalog.episodes.filter(row => ($('split').value === 'all' || row.split === $('split').value) && ($('dataset').value === 'all' || row.dataset === $('dataset').value) && (!query || row._search.includes(query)));
    page = 0;
    if (!filtered.length) {
      request++; current = null; selectedKey = ''; video.pause();
      $('episode-content').hidden = true; $('detail').setAttribute('aria-busy','false');
      notice('没有匹配的轨迹，请调整搜索或筛选。');
    } else if (selectFirst) {
      const chosen = filtered.find(r => r.parent_episode_key === selectedKey) || filtered[0];
      page = Math.floor(filtered.indexOf(chosen) / pageSize); select(chosen.parent_episode_key);
    }
    directory(); updateURL();
  }
  function seek(frame) {
    if (!current) return;
    const target = Math.max(0, Math.min(current.total_frames - 1, Math.round(frame)));
    video.pause();
    if (video.readyState >= 1) video.currentTime = (target + 0.01) / current.fps;
    else pendingFrame = target;
    showFrame(target);
  }
  function showFrame(frame) {
    if (!current) return;
    $('frame').textContent = `${frame} / ${current.total_frames - 1} 帧`;
    const target = current.atomic_training_targets.find(t => t.start_frame <= frame && frame <= t.end_frame);
    if (!target || activeId === target.atomic_task_id) return;
    activeId = target.atomic_task_id;
    $('active-oa').textContent = target.ongoing_action; $('active-om').textContent = target.ongoing_mission;
    $('active-context').textContent = target.context;
    $('active-range').textContent = `${target.start_frame}–${target.end_frame} 帧 · ${target.active_mission_id}`;
    document.querySelectorAll('[data-segment]').forEach(node => node.classList.toggle('current', node.dataset.segment === target.atomic_task_id || node.dataset.segment === target.short_term_mission_id));
  }
  function segments(rows, type) {
    const atom = type === 'atomic', label = atom ? 'atomic_task' : 'mission', id = atom ? 'atomic_task_id' : 'mission_id';
    const prefix = atom ? 'A' : 'M';
    $(`${type}-track`).innerHTML = rows.map((row, i) => `<button data-segment="${escape(row[id])}" data-frame="${row.start_frame}" style="width:${100 * (row.end_frame-row.start_frame+1) / current.total_frames}%" title="${escape(row[label])}: ${row.start_frame}–${row.end_frame}" aria-label="${prefix}${i+1}: ${escape(row[label])}">${prefix}${i+1}</button>`).join('');
    $(atom ? 'atomics' : 'missions').innerHTML = rows.map((row, i) => `<button class="segment" data-segment="${escape(row[id])}" data-frame="${row.start_frame}"><b>${prefix}${i+1}</b><span>${escape(row[label])}${atom ? `<small>${escape(row.boundary_source || '')}</small>` : `<small>${row.atomic_task_ids.length} 个动作</small>`}</span><small>${row.start_frame}–${row.end_frame} 帧<br>${(row.start_frame/current.fps).toFixed(2)}–${((row.end_frame+1)/current.fps).toFixed(2)} s</small></button>`).join('');
  }
  async function select(key) {
    const item = catalog.episodes.find(r => r.parent_episode_key === key);
    if (!item) return;
    const ticket = ++request;
    selectedKey = key; current = null; video.pause(); activeId = ''; pendingFrame = null;
    $('episode-content').hidden = true; $('detail').setAttribute('aria-busy','true');
    notice('正在载入轨迹标注…'); directory(); updateURL();
    try {
      const records = await shard(item.dataset);
      if (ticket !== request) return;
      current = records.get(key);
      if (!current) throw new Error('数据分片中缺少该轨迹。');
      $('episode-tag').textContent = `${current.dataset_label} / ${splitName[current.split]}`;
      $('instruction').textContent = current.full_episode_instruction;
      $('episode-key').textContent = current.parent_episode_key;
      $('episode-meta').textContent = `${fmt(current.total_frames)} 帧 · ${current.fps} fps · ${(current.total_frames/current.fps).toFixed(1)} 秒 · ${current.training_views.length} 个训练视角 · task ${current.task_id} / episode ${current.episode_id}`;
      $('annotation-note').hidden = !current.validation_notes.length;
      $('annotation-note').textContent = current.validation_notes.map(n => `${n.mission_id}: ${n.message} 意图区间 ${n.mission_frames.join('–')}；动作区间 ${n.member_action_frames.join('–')}。`).join(' ');
      $('video-error').hidden = true; $('video-link').href = current.video_url; video.src = current.video_url; video.load();
      $('atomic-count').textContent = `(${current.atomic_tasks.length})`; $('mission-count').textContent = `(${current.short_term_missions.length})`;
      segments(current.short_term_missions, 'mission'); segments(current.atomic_tasks, 'atomic');
      $('system-prompt').textContent = current.system_prompt;
      $('targets').innerHTML = current.atomic_training_targets.map((t,i) => `<article class="training-target"><h4>A${i+1} · ${t.start_frame}–${t.end_frame} 帧 <button data-frame="${t.start_frame}">定位</button></h4><label>User prompt</label><pre>${escape(t.user_prompt)}</pre><label>Target output</label><pre>${escape(t.target_output)}</pre></article>`).join('');
      $('provenance').textContent = `标注来源：${current.hierarchy_provenance}；源数据 reviewed：${current.reviewed ? 'true' : 'false'}。`;
      $('views').innerHTML = current.training_views.map(v => `<div class="view-item"><b>${escape(v.view_type)}${v.is_primary ? ' · 主视角' : ''}</b> <span class="mono">${escape(v.camera_key)}</span></div>`).join('');
      $('episode-content').hidden = false; notice(''); $('detail').setAttribute('aria-busy','false'); showFrame(0);
    } catch (error) {
      if (ticket !== request) return;
      current = null; notice(`${error.message}。点击目录中的轨迹可重试。`); $('detail').setAttribute('aria-busy','false');
    }
  }
  function move(delta) {
    const index = filtered.findIndex(r => r.parent_episode_key === selectedKey) + delta;
    if (index >= 0 && index < filtered.length) {page = Math.floor(index/pageSize); select(filtered[index].parent_episode_key);}
  }
  $('directory').addEventListener('click', e => {const item = e.target.closest('[data-key]'); if (item) select(item.dataset.key);});
  $('detail').addEventListener('click', e => {const item = e.target.closest('[data-frame]'); if (item) seek(Number(item.dataset.frame));});
  $('split').addEventListener('change', () => filter()); $('dataset').addEventListener('change', () => filter());
  let searchTimer; $('search').addEventListener('input', () => {clearTimeout(searchTimer); searchTimer = setTimeout(() => filter(), 150);});
  $('page-prev').onclick = () => {page--; directory();}; $('page-next').onclick = () => {page++; directory();};
  $('previous').onclick = () => move(-1); $('next').onclick = () => move(1);
  $('frame-back').onclick = () => seek(Math.floor(video.currentTime * current.fps + 1e-5) - 1);
  $('frame-next').onclick = () => seek(Math.floor(video.currentTime * current.fps + 1e-5) + 1);
  video.addEventListener('timeupdate', () => {if (current && pendingFrame === null) showFrame(Math.max(0,Math.min(current.total_frames-1,Math.floor(video.currentTime*current.fps + 1e-5))));});
  video.addEventListener('loadedmetadata', () => {if (pendingFrame !== null) {const f = pendingFrame; pendingFrame = null; seek(f);}});
  video.addEventListener('error', () => {$('video-error').hidden = false;});
  $('download-episode').onclick = () => {if (current) download(`v3_${current.dataset}_${current.task_id}_${current.episode_id}.json`,current);};
  $('copy-link').onclick = async () => {try {await navigator.clipboard.writeText(location.href); $('copy-link').textContent = '已复制'; setTimeout(() => {$('copy-link').textContent = '复制链接';}, 1800);} catch {notice(`本条链接：${location.href}`);}};
  $('download-split').onclick = async () => {
    const button = $('download-split'), split = $('split').value;
    button.disabled = true; button.textContent = '正在准备完整标注…';
    try {
      const maps = await Promise.all(Object.keys(catalog.datasets).map(shard));
      const all = new Map(maps.flatMap(m => [...m.entries()]));
      const episodes = catalog.episodes.filter(r => split === 'all' || r.split === split).map(r => all.get(r.parent_episode_key));
      download(`intention_v3_clean_${split}.json`,{annotation_version:'v3-clean-final-training',split,episode_count:episodes.length,episodes});
      button.textContent = `已导出 ${fmt(episodes.length)} 条`;
    } catch (error) {notice(error.message); button.textContent = '下载失败，点击重试';}
    finally {button.disabled = false; setTimeout(() => {button.textContent = '下载当前划分的全部标注 JSON';},2500);}
  };
  async function boot() {
    try {
      catalog = await getJSON('data/index.json');
      catalog.episodes.forEach(r => {r._search = `${r.parent_episode_key} ${r.task_id} ${r.episode_id} ${r.dataset_label} ${r.full_episode_instruction} ${r.search_text}`.toLowerCase();});
      const s = catalog.summary;
      $('stats').innerHTML = [[s.episodes,'轨迹 · 5,500 / 550 / 550'],[s.atomic_actions,'原子动作标注 · OA'],[s.short_term_missions,'短期意图标注 · OM'],[s.train_sampling_records,'训练采样记录 · 六种采样'],[s.datasets,'数据来源']].map(([n,label]) => `<div class="stat"><strong>${fmt(n)}</strong><span>${label}</span></div>`).join('');
      $('dataset').innerHTML += Object.entries(catalog.datasets).map(([key,d]) => `<option value="${escape(key)}">${escape(d.label)} · ${d.episodes}</option>`).join('');
      const params = new URLSearchParams(location.search), requested = catalog.episodes.find(r => r.parent_episode_key === params.get('episode'));
      $('split').value = Object.hasOwn(splitName,params.get('split')) ? params.get('split') : (requested?.split || 'train');
      $('dataset').value = catalog.datasets[params.get('dataset')] ? params.get('dataset') : 'all';
      $('search').value = params.get('q') || '';
      if (requested) selectedKey = requested.parent_episode_key;
      filter();
    } catch (error) {notice(`目录加载失败：${error.message}。请刷新重试。`); $('detail').setAttribute('aria-busy','false');}
  }
  boot();
})();

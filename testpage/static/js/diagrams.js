/* Play the paper's demonstrations against their recorded control-mode timeline. */
(() => {
  "use strict";
  const root = document.querySelector(".handoff-diagram");
  if (!root) return;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const names = { human: "Human teleop", vla: "VLA control" };
  const colors = { human: "#e69f00", vla: "#0072b2" };
  const timeText = seconds => {
    const s = Math.max(0, Math.floor(seconds));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  };
  const icons = {
    play: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3 16 10 5 17Z"/></svg>',
    pause: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3h4v14H5zM12 3h4v14h-4z"/></svg>'
  };

  class Rollout {
    constructor(element, data) {
      this.element = element;
      this.videos = [...element.querySelectorAll("video")];
      this.clips = this.videos.map(video => data[video.dataset.rollout]);
      this.offsets = [];
      this.duration = this.clips.reduce((t, clip) => { this.offsets.push(t); return t + clip.duration; }, 0);
      this.phases = this.clips.flatMap((clip, i) => clip.phases.map(phase => ({
        ...phase, start: phase.start + this.offsets[i], end: phase.end + this.offsets[i]
      })));
      this.range = element.querySelector('input[type="range"]');
      this.toggle = element.querySelector(".rollout-toggle");
      this.mode = element.querySelector(".rollout-mode");
      this.clock = element.querySelector(".rollout-time");
      this.tooltip = element.querySelector(".mode-tooltip");
      this.timeline = element.querySelector(".mode-timeline");
      this.missions = [...element.querySelectorAll("[data-mission-index]")];
      this.index = 0;
      this.visible = false;
      this.loaded = false;
      this.dragging = false;
      this.wantsPlay = !reducedMotion.matches;
      this.explicitPlay = false;
      this.range.max = this.duration;
      this.timeline.style.setProperty("--mode-gradient", "linear-gradient(to right," +
        this.phases.map(p => colors[p.mode] + " " + p.start / this.duration * 100 + "% " + p.end / this.duration * 100 + "%").join(",") + ")");
      this.videos.forEach((video, i) => {
        video.muted = true;
        video.defaultPlaybackRate = 2;
        video.playbackRate = 2;
        video.addEventListener("timeupdate", () => { if (i === this.index && !this.dragging) this.render(); });
        video.addEventListener("loadedmetadata", () => {
          video.playbackRate = 2;
          if (video.dataset.seekTo !== undefined) {
            video.currentTime = Math.min(Number(video.dataset.seekTo), video.duration - .04);
            delete video.dataset.seekTo;
          }
          if (i === this.index) this.syncPlayback();
        });
        video.addEventListener("ended", () => {
          if (i !== this.index) return;
          this.seek(i + 1 < this.videos.length ? this.offsets[i + 1] : 0);
          this.syncPlayback();
        });
        video.addEventListener("click", () => {
          if (i !== this.index) {
            this.seek(this.offsets[i]);
            this.wantsPlay = this.explicitPlay = true;
          } else {
            this.wantsPlay = !this.wantsPlay;
            this.explicitPlay = this.wantsPlay;
          }
          this.syncPlayback();
        });
        video.addEventListener("error", () => {
          if (i === this.index) {
            this.wantsPlay = false;
            this.clock.textContent = "Video unavailable";
            this.updateButton();
          }
        });
      });
      this.toggle.addEventListener("click", () => {
        this.load();
        this.wantsPlay = !this.wantsPlay;
        this.explicitPlay = this.wantsPlay;
        this.syncPlayback();
      });
      this.missions.forEach((button, i) => button.addEventListener("click", () => {
        this.load();
        this.seek(this.offsets[i]);
        this.wantsPlay = this.explicitPlay = true;
        this.syncPlayback();
      }));
      this.range.addEventListener("pointerdown", () => {
        this.load();
        this.dragging = true;
        this.videos.forEach(video => video.pause());
      });
      this.range.addEventListener("input", () => {
        this.load();
        this.seek(Number(this.range.value));
        this.showTooltip(Number(this.range.value));
      });
      const finishSeek = () => {
        this.dragging = false;
        this.tooltip.hidden = true;
        this.syncPlayback();
      };
      this.range.addEventListener("change", finishSeek);
      this.range.addEventListener("pointerup", finishSeek);
      this.range.addEventListener("pointercancel", finishSeek);
      this.range.addEventListener("blur", finishSeek);
      this.range.addEventListener("pointermove", event => {
        if (event.pointerType === "touch") return;
        const box = this.range.getBoundingClientRect();
        this.showTooltip(Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)) * this.duration);
      });
      this.range.addEventListener("pointerleave", () => { if (!this.dragging) this.tooltip.hidden = true; });
      this.render();
    }
    load() {
      if (this.loaded) return;
      this.loaded = true;
      this.videos.forEach(video => { video.src = video.dataset.src; video.load(); });
    }
    currentTime() {
      const video = this.videos[this.index];
      return this.offsets[this.index] + (video.dataset.seekTo !== undefined ? Number(video.dataset.seekTo) : video.currentTime);
    }
    phaseAt(time) {
      return this.phases.find(p => time >= p.start && time < p.end) || this.phases[this.phases.length - 1];
    }
    seek(time) {
      time = Math.max(0, Math.min(this.duration - .05, time));
      const index = this.offsets.findIndex((offset, i) => time < offset + this.clips[i].duration);
      this.index = Math.max(0, index);
      this.videos.forEach((video, i) => {
        const desired = i < this.index ? this.clips[i].duration - .07 : i > this.index ? 0 : time - this.offsets[i];
        video.pause();
        if (video.readyState >= 1) video.currentTime = Math.max(0, Math.min(desired, video.duration - .04));
        else video.dataset.seekTo = desired;
      });
      this.render(time);
      if (!this.dragging) this.syncPlayback();
    }
    showTooltip(time) {
      const width = this.timeline.clientWidth;
      this.tooltip.textContent = timeText(time) + " · " + names[this.phaseAt(time).mode];
      this.tooltip.hidden = false;
      const half = this.tooltip.offsetWidth / 2;
      this.tooltip.style.left = Math.max(half, Math.min(width - half, time / this.duration * width)) + "px";
    }
    updateButton() {
      this.toggle.innerHTML = icons[this.wantsPlay ? "pause" : "play"];
      this.toggle.setAttribute("aria-label", (this.wantsPlay ? "Pause " : "Play ") + this.element.dataset.playerLabel);
    }
    render(time = this.currentTime()) {
      const phase = this.phaseAt(time);
      this.range.value = time;
      this.range.setAttribute("aria-valuetext", timeText(time) + ", " + names[phase.mode] + ", " + this.clips[this.index].title);
      this.mode.textContent = names[phase.mode];
      this.mode.dataset.mode = phase.mode;
      this.clock.textContent = timeText(time) + " / " + timeText(this.duration);
      this.videos.forEach((video, i) => {
        video.parentElement.classList.toggle("is-current", i === this.index);
        video.parentElement.dataset.currentMode = i === this.index ? phase.mode : "";
      });
      this.missions.forEach((button, i) => {
        if (i === this.index) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
      });
      this.updateButton();
    }
    syncPlayback() {
      const shouldPlay = this.visible && !document.hidden && this.wantsPlay && !this.dragging;
      this.videos.forEach((video, i) => {
        if (i === this.index && shouldPlay && video.readyState >= 1) {
          video.play().catch(error => {
            if (error.name === "AbortError") return;
            if (i === this.index && !this.dragging && this.visible && !document.hidden) {
              this.wantsPlay = false;
              this.updateButton();
            }
          });
        } else video.pause();
      });
      this.updateButton();
    }
  }
  fetch("static/diagrams/rollouts/timelines.json")
    .then(response => { if (!response.ok) throw new Error("Timeline unavailable"); return response.json(); })
    .then(data => {
      const players = [...root.querySelectorAll("[data-rollout-player]")].map(el => new Rollout(el, data));
      const lookup = new Map(players.map(player => [player.element, player]));
      const observer = new IntersectionObserver(entries => entries.forEach(entry => {
        const player = lookup.get(entry.target);
        player.visible = entry.isIntersecting;
        if (player.visible) player.load();
        player.syncPlayback();
      }), { threshold: .15 });
      players.forEach(player => observer.observe(player.element));
      document.addEventListener("visibilitychange", () => players.forEach(player => player.syncPlayback()));
      reducedMotion.addEventListener("change", () => players.forEach(player => {
        if (!player.explicitPlay) player.wantsPlay = !reducedMotion.matches;
        player.syncPlayback();
      }));
    }).catch(() => {
      // Keep the original paper figure visible if interaction cannot initialize.
      root.hidden = true;
      document.querySelector(".handoff-static").hidden = false;
    });
})();

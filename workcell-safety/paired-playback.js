'use strict';

function releaseMediaUrl(url) {
  const build = document.documentElement.dataset.build;
  if (!build || !url || url.startsWith('#')) return url;
  const resource = new URL(url, document.baseURI);
  if (resource.origin !== location.origin) return url;
  resource.searchParams.set('v', build);
  return resource.href;
}

function atReplayEnd(video) {
  return video.ended || (video.paused && Number.isFinite(video.duration) &&
    video.duration - video.currentTime <= 0.008);
}

function pairPosition(videos) {
  if (videos.every(atReplayEnd)) return 0;
  return videos.find(video => !atReplayEnd(video)).currentTime;
}

function syncLiveReplays(videos) {
  const moving = videos.filter(video => !atReplayEnd(video));
  if (moving.length !== 2 || moving.some(video => video.readyState < 3)) return;
  const [first, second] = moving;
  if (Math.abs(first.currentTime - second.currentTime) > 0.15) second.currentTime = first.currentTime;
}

function startReplays(videos, time, rate = 1) {
  return Promise.all(videos.map(video => {
    const end = Number.isFinite(video.duration) ? video.duration : Infinity;
    video.currentTime = Math.min(time, end);
    video.playbackRate = rate * video.defaultPlaybackRate;
    if (time < end - 0.008) return video.play();
    video.pause();
  }));
}

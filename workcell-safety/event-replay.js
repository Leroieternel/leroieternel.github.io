'use strict';

function renderEventReplay(clip, filmRoot, imageRoot) {
  const section = document.getElementById('event-replay');
  section.replaceChildren();
  section.hidden = !clip;
  if (!clip) return;
  const heading = document.createElement('h2');
  heading.textContent = clip.title;
  const caption = document.createElement('p');
  caption.textContent = clip.caption;
  const video = document.createElement('video');
  video.controls = true;
  video.playsInline = true;
  video.preload = 'metadata';
  video.setAttribute('aria-label', clip.title);
  video.style.cssText = 'display:block;width:100%;max-width:32rem;height:auto;aspect-ratio:960/1192';
  video.poster = imageRoot + '/' + clip.poster;
  video.src = filmRoot + '/' + clip.file;
  section.append(heading, caption, video);
}

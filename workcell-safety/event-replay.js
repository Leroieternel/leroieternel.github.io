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
  const wide = clip.width > clip.height;
  video.style.cssText = 'display:block;width:100%;height:auto;max-width:' + (wide ? '75rem' : '32rem');
  video.style.aspectRatio = clip.width && clip.height ? clip.width + ' / ' + clip.height : 'auto';
  video.poster = releaseMediaUrl(imageRoot + '/' + clip.poster);
  video.src = releaseMediaUrl(filmRoot + '/' + clip.file);
  section.append(heading, caption, video);
}

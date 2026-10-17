(() => {
  document.addEventListener('keydown', event => {
    if (!['ArrowLeft','ArrowRight'].includes(event.key) || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.defaultPrevented) return;
    const target = event.target;
    if (target.closest?.('input,textarea,select,[role="slider"],[role="textbox"],[contenteditable]:not([contenteditable="false"])') || document.querySelector('dialog[open]')) return;
    const video = document.getElementById('v');
    if (!video || !video.readyState) return;
    const end = Number.isFinite(video.duration) ? video.duration : video.seekable.length ? video.seekable.end(video.seekable.length-1) : NaN;
    if (!Number.isFinite(end)) return;
    event.preventDefault();
    video.currentTime = Math.max(0, Math.min(end, video.currentTime + (event.key === 'ArrowRight' ? 10 : -10)));
  });
})();

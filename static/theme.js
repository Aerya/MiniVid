(() => {
  const root = document.documentElement;
  const validColor = value => /^#[0-9a-f]{6}$/i.test(value || '');
  function apply(theme, accent, background) {
    root.dataset.theme = theme;
    root.classList.toggle('light', theme === 'light');
    if (validColor(accent)) root.style.setProperty('--accent', accent);
    if (theme === 'custom' && validColor(background)) root.style.setProperty('--bg', background);
    else root.style.removeProperty('--bg');
  }
  apply(root.dataset.theme, root.dataset.accent, root.dataset.background);
  const form = document.getElementById('theme-form');
  if (!form) return;
  form.elements.theme.value = root.dataset.theme || 'dark';
  form.addEventListener('input', () => apply(form.elements.theme.value, form.elements.accent.value, form.elements.background.value));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const status = document.getElementById('theme-status');
    try {
      const response = await fetch('/api/preferences', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(Object.fromEntries(new FormData(form)))});
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error('Enregistrement refusé');
      status.textContent = 'Thème enregistré';
    } catch (error) { status.textContent = error.message; }
  });
})();

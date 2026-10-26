(() => {
    const initialScan = document.getElementById('library-initial-scan');
    if (initialScan && ['/home', '/browse'].includes(location.pathname)) {
      const initialCount = Number(initialScan.dataset.count);
      const status = document.createElement('span');
      const refresh = document.createElement('a');
      status.textContent = initialScan.textContent;
      refresh.href = location.href;
      refresh.textContent = 'Actualiser pour afficher les nouvelles vidéos';
      refresh.hidden = true;
      initialScan.replaceChildren(status, ' ', refresh);
      const poll = async () => {
        try {
          const response = await fetch('/api/maintenance/progress', {credentials:'same-origin'});
          const scan = await response.json();
          if (response.ok && scan.ok) {
            const count = Number(scan.indexed);
            const finished = !scan.running || scan.kind !== 'initial';
            if (Number.isInteger(count) && count >= 0) {
              status.textContent = `${finished ? 'Vérification de la bibliothèque terminée.' : 'Vérification de la bibliothèque en cours.'} Vidéos disponibles : ${count}.`;
              refresh.hidden = count === initialCount;
            }
            if (finished) return;
          }
        } catch (_) {}
        setTimeout(poll, 5000);
      };
      setTimeout(poll, 5000);
    }
    const form = document.getElementById('library-controls');
    if (!form) return;
    const PREFS = JSON.parse(form.dataset.prefs || '{}');
    const header = form.closest('.app-topbar');
    const updateHeight = () => document.documentElement.style.setProperty('--topbar-height', Math.ceil(header.getBoundingClientRect().height) + 'px');
    new ResizeObserver(updateHeight).observe(header);
    updateHeight();
    async function savePrefs(patch) {
      try {
        await fetch('/api/preferences', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch)
        });
      } catch (_) {}
    }

    function applyThumbSize(px) {
      const val = parseInt(px, 10) || 240;
      document.documentElement.style.setProperty('--thumb-h', val + 'px');
      const is169 = document.documentElement.classList.contains('ratio-16-9');
      if (is169) {
        const cardMin = val <= 195 ? 220 : (val <= 245 ? 280 : 350);
        document.documentElement.style.setProperty('--card-min', cardMin + 'px');
      } else {
        document.documentElement.style.setProperty('--card-min', Math.max(200, Math.floor(val * 1.08)) + 'px');
      }
    }

    function applyThumbRatio(ratio) {
      const is169 = ratio !== 'square';
      document.documentElement.classList.toggle('ratio-16-9', is169);
      document.documentElement.classList.toggle('ratio-square', !is169);
      const ratioEl = document.getElementById('thumbRatio');
      if (ratioEl) ratioEl.value = is169 ? '16-9' : 'square';
      applyThumbSize(document.getElementById('thumb')?.value || 240);
    }

    (function initPrefs() {
      const thumb = document.getElementById('thumb');
      if (thumb) {
        thumb.value = String(PREFS.thumb_px || 240);
        applyThumbSize(thumb.value);
        thumb.addEventListener('change', () => {
          applyThumbSize(thumb.value);
          savePrefs({ thumb_px: parseInt(thumb.value, 10) || 240 });
        });
      }

      const ratioEl = document.getElementById('thumbRatio');
      const savedRatio = localStorage.getItem('minivid_thumb_ratio') || PREFS.thumb_ratio || '16-9';
      applyThumbRatio(savedRatio);
      if (ratioEl) {
        ratioEl.addEventListener('change', () => {
          applyThumbRatio(ratioEl.value);
          localStorage.setItem('minivid_thumb_ratio', ratioEl.value);
          savePrefs({ thumb_ratio: ratioEl.value });
        });
      }

      ['sort','per','read','mix'].forEach(id => {
        const el = document.getElementById(id);
        el?.addEventListener('change', async () => {
          if(id !== 'sort') await savePrefs({[id]:el.value});
          form.requestSubmit();
        });
      });

      const smart = document.getElementById('smartSort');
      if (smart) {
        smart.addEventListener('change', async () => {
          await savePrefs({ smart: smart.checked });
          form.requestSubmit();
        });
      }
    })();

    (function filtersPopover() {
      const btn = document.getElementById('filtersDropdownBtn');
      const pop = document.getElementById('filtersPopover');
      const close = document.getElementById('filtersCloseBtn');
      if (!btn || !pop) return;
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const willShow = pop.hidden;
        pop.hidden = !willShow;
        btn.setAttribute('aria-expanded', willShow ? 'true' : 'false');
      });
      close?.addEventListener('click', (e) => {
        e.stopPropagation();
        pop.hidden = true;
        btn.setAttribute('aria-expanded', 'false');
      });
      pop.addEventListener('click', (e) => e.stopPropagation());
      document.addEventListener('keydown', event => {if(event.key === 'Escape' && !pop.hidden){pop.hidden=true;btn.setAttribute('aria-expanded','false');btn.focus();}});
      document.addEventListener('click', () => {
        if (!pop.hidden) {
          pop.hidden = true;
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    })();

    (function viewModeSwitcher() {
      const btns = document.querySelectorAll('.view-mode-btn');
      if (!btns.length) return;
      let saved = localStorage.getItem('minivid_view_mode') || 'cards';
      if (saved !== 'wall') saved = 'cards';

      function setView(mode) {
        document.querySelectorAll('.grid').forEach(g => {
          g.classList.remove('view-cards', 'view-wall', 'view-list');
          g.classList.add('view-' + mode);
        });
        btns.forEach(b => {
          b.classList.toggle('active', b.dataset.view === mode);
        });
        localStorage.setItem('minivid_view_mode', mode);
      }

      btns.forEach(b => {
        b.addEventListener('click', (e) => {
          e.preventDefault();
          setView(b.dataset.view);
        });
      });

      setView(saved);
    })();



})();

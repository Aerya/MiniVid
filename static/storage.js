/* Storage review: local display preferences, server-side policy and deletion checks. */
(() => {
  const $ = id => document.getElementById(id);
  const selected = new Set();
  let page = 1;
  let lastResult = null;
  let preview = null;
  let layout = localStorage.getItem('minivid_storage_layout') === 'gallery' ? 'gallery' : 'list';
  let width = ['standard', 'wide', 'full'].includes(localStorage.getItem('minivid_storage_width'))
    ? localStorage.getItem('minivid_storage_width') : 'standard';
  const size = value => (Number(value || 0) / 1073741824).toLocaleString('fr-FR', {maximumFractionDigits: 2}) + ' Gio';
  const date = value => value ? new Date(Number(value) * 1000).toLocaleDateString('fr-FR') : 'Jamais';
  const node = (tag, label, className) => {
    const item = document.createElement(tag);
    if (label != null) item.textContent = label;
    if (className) item.className = className;
    return item;
  };
  async function json(url, options = {}) {
    const response = await fetch(url, {credentials:'same-origin', ...options});
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || String(response.status));
    return data;
  }
  const post = (url, data) => json(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});

  function displayMode() {
    document.querySelector('.storage-page').dataset.width = width;
    $('storage-gallery').hidden = layout !== 'gallery';
    $('storage-table-wrap').hidden = layout !== 'list';
    $('storage-layout').textContent = layout === 'gallery' ? 'Affichage : vignettes' : 'Affichage : liste';
    $('storage-width').textContent = 'Largeur : ' + ({standard:'standard', wide:'large', full:'plein écran'}[width]);
    $('storage-width').dataset.mode = width;
    $('storage-width').setAttribute(
      'aria-label',
      'Changer la largeur. Largeur actuelle : ' +
        ({standard:'standard', wide:'large', full:'plein écran'}[width])
    );
    $('storage-layout').setAttribute('aria-pressed', String(layout === 'gallery'));
  }
  function selectBox(id) {
    const box = document.createElement('input');
    box.type = 'checkbox'; box.checked = selected.has(id); box.setAttribute('aria-label', 'Sélectionner ce média');
    box.addEventListener('change', () => {
      if (box.checked && selected.size >= 100 && !selected.has(id)) {
        box.checked = false; alert('Sélection limitée à 100 médias.'); return;
      }
      if (box.checked) selected.add(id); else selected.delete(id);
      document.querySelectorAll('input[data-storage-id]').forEach(other => {
        if (other.dataset.storageId === id && other !== box) other.checked = box.checked;
      });
      selectionStatus();
    });
    box.dataset.storageId = id;
    return box;
  }
  function thumbnail(item, className) {
    const link = node('a', null, className);
    link.href = '/watch/' + encodeURIComponent(item.id);
    const image = document.createElement('img');
    image.src = '/thumb/' + encodeURIComponent(item.id) + '.jpg';
    image.alt = ''; image.loading = 'lazy'; image.decoding = 'async';
    image.addEventListener('error', () => {
      image.onerror = null;
      image.src = '/static/placeholder.svg';
      link.classList.add('storage-no-image');
    }, {once:true});
    link.append(image);
    return link;
  }
  function mediaAction(item) {
    const button = node('button', 'Supprimer…', 'btn btn-danger'); button.type = 'button';
    button.addEventListener('click', async () => {
      try {
        const info = await json('/api/media/' + encodeURIComponent(item.id) + '/management');
        if (!info.can_delete) throw new Error(info.torrent_error || 'Suppression désactivée pour cette source');
        const what = info.delete_mode === 'torrent' ? `${info.torrents.length} torrent(s) et leurs données` : 'le fichier local';
        if (prompt(`Supprimer ${what} définitivement ?${info.favorite ? ' Attention : favori.' : ''}\nSaisissez exactement : ${info.name}`) !== info.name) return;
        button.disabled = true;
        await post('/api/media/' + encodeURIComponent(item.id) + '/delete', {confirmation:info.name});
        selected.delete(item.id); await loadStorage();
      } catch (error) { alert('Suppression refusée : ' + error.message); }
      finally { button.disabled = false; }
    });
    return button;
  }
  function renderItems(items, admin) {
    const rows = $('storage-rows'), gallery = $('storage-gallery');
    rows.replaceChildren(); gallery.replaceChildren();
    for (const item of items) {
      const link = node('a', item.name); link.href = '/watch/' + encodeURIComponent(item.id);
      const row = document.createElement('tr');
      const check = document.createElement('td'); if (admin) check.append(selectBox(item.id)); row.append(check);
      const title = document.createElement('td'); title.className = 'storage-media-cell';
      const titleWrap = node('div', null, 'storage-media-content');
      titleWrap.append(thumbnail(item, 'storage-row-image'));
      const titleText = document.createElement('div'); titleText.append(link, node('small', item.root_name || ''));
      titleWrap.append(titleText); title.append(titleWrap); row.append(title);
      [size(item.size), date(item.mtime), `${item.starts || 0} / ${item.completions || 0} terminées`,
       item.max_percent ? `${Math.round(item.max_percent)} %` : '—', date(item.last_played),
       item.favorite ? '★ Favori' : ({candidate:'Candidat', protect:'Protégé'}[item.policy] || '—')]
        .forEach(value => row.append(node('td', value)));
      const action = document.createElement('td'); if (admin) action.append(mediaAction(item)); row.append(action);
      rows.append(row);

      const card = node('article', null, 'storage-media-card');
      const imageWrap = node('div', null, 'storage-image-wrap');
      imageWrap.append(thumbnail(item, 'storage-card-image'));
      if (admin) { const cardCheck = node('label', null, 'storage-card-check'); cardCheck.append(selectBox(item.id), ' Sélectionner'); imageWrap.append(cardCheck); }
      card.append(imageWrap);
      const body = node('div', null, 'storage-card-content');
      const cardLink = node('a', item.name, 'storage-card-title'); cardLink.href = '/watch/' + encodeURIComponent(item.id);
      body.append(cardLink, node('small', `${item.root_name || ''} · ${size(item.size)}`),
        node('small', `Fichier du ${date(item.mtime)} · ${item.starts || 0} démarrage(s) · max. ${Math.round(item.max_percent || 0)} %`),
        node('small', `Dernière lecture : ${date(item.last_played)}`));
      if (item.favorite || item.policy !== 'none') body.append(node('strong', item.favorite ? '★ Favori' : item.policy === 'protect' ? 'Protégé' : 'Candidat'));
      if (admin) body.append(mediaAction(item));
      card.append(body); gallery.append(card);
    }
  }
  function renderCopies(result) {
    const copies = $('storage-copies'); copies.replaceChildren();
    if (!result.copies.length) copies.textContent = 'Aucune copie physique vérifiée.';
    result.copies.forEach(group => {
      const wrap = node('div', null, 'storage-group');
      wrap.append(node('strong', `${group.items.length} chemins · jusqu’à ${size(group.estimated_bytes)} récupérables`));
      const list = node('ul');
      group.items.forEach((id, index) => {
        const li = node('li'), keep = document.createElement('input'), link = node('a', group.names[index]);
        keep.type = 'radio'; keep.name = 'keep-' + group.digest; keep.value = id; keep.checked = index === 0;
        link.href = '/watch/' + encodeURIComponent(id); li.append(keep, ' Garder ', link); list.append(li);
      });
      wrap.append(list);
      if (result.admin) {
        const button = node('button', 'Supprimer les autres copies', 'btn btn-danger');
        button.onclick = async () => {
          const keep = wrap.querySelector('input:checked')?.value;
          if (!confirm(`Conserver ${group.names[group.items.indexOf(keep)]} et supprimer les autres copies ? Les médias liés à BitTorrent ou protégés sont bloqués.`)) return;
          button.disabled = true;
          try { await post('/api/storage/duplicates/delete', {digest:group.digest, keep, confirmation:'SUPPRIMER'}); await loadStorage(); }
          catch (error) { alert('Suppression refusée : ' + error.message); button.disabled = false; }
        };
        wrap.append(button);
      }
      copies.append(wrap);
    });
    const links = $('storage-links'); links.replaceChildren();
    if (!result.links.length) links.textContent = 'Aucun lien physique partagé dans les sources.';
    result.links.forEach(group => {
      const wrap = node('div', null, 'storage-group');
      wrap.append(node('strong', `${group.items.length} chemins · même fichier physique · aucune copie supplémentaire`));
      const list = node('ul');
      group.items.forEach((id, index) => {
        const li = node('li'), link = node('a', group.names[index]); link.href = '/watch/' + encodeURIComponent(id);
        li.append(link); list.append(li);
      }); wrap.append(list); links.append(wrap);
    });
  }
  function selectionStatus() {
    $('storage-selected-count').textContent = `${selected.size} sélectionné(s)`;
    $('storage-preview-selection').disabled = !selected.size || selected.size > 100;
    if (lastResult) {
      const visible = lastResult.items.map(item => item.id);
      $('storage-select-page').checked = !!visible.length && visible.every(id => selected.has(id));
      $('storage-select-page').indeterminate = visible.some(id => selected.has(id)) && !visible.every(id => selected.has(id));
    }
  }
  async function loadStorage() {
    const query = new URLSearchParams({filter:$('storage-filter').value, sort:$('storage-sort').value, page});
    const result = await json('/api/storage?' + query);
    lastResult = result;
    const mounts = $('storage-mounts'); mounts.replaceChildren();
    result.mounts.forEach(mount => mounts.append(node('div', `${mount.name} (${mount.path}) — ${size(mount.free)} libres sur ${size(mount.total)} (${(mount.free / mount.total * 100).toFixed(1)} %)`)));
    $('storage-scan-status').textContent = result.scan.running ? result.scan.message :
      result.scanned_at ? `Dernière analyse : ${date(result.scanned_at)}. ${result.scan.message || ''}` : 'Analyse à lancer.';
    renderCopies(result); renderItems(result.items, result.admin);
    $('storage-total').textContent = `(${result.count})`;
    $('storage-page').textContent = `${page} / ${Math.max(1, Math.ceil(result.count / 100))}`;
    $('storage-prev').disabled = page <= 1;
    $('storage-next').disabled = page * 100 >= result.count;
    $('storage-select-page').disabled = !result.admin || !result.items.length;
    selectionStatus(); displayMode();
  }
  async function loadAutomation() {
    const data = await json('/api/storage/automation');
    $('automation-enabled').checked = !!data.settings.enabled;
    $('automation-owner').value = data.settings.owner_id || '';
    $('automation-here').dataset.instance = data.instance_id;
    $('automation-status').textContent = data.active ? 'Actif sur cette instance.' :
      data.sync_configured ? 'Suspendu ou exécuté par une autre instance.' : 'Synchronisation non configurée : activation impossible.';
    $('federation-status').textContent = `Fédération : ${data.sync_configured ? data.peer_count + ' pair(s) configuré(s)' : 'non configurée'} · Identifiant de cette instance : ${data.instance_id}`;
  }
  function defaultPayload() {
    return {ratio:Number($('default-ratio').value), seed_seconds:Math.round(Number($('default-days').value) * 86400),
      seed_operator:$('default-operator').value, trigger_mode:$('default-trigger').value,
      free_below:Number($('default-below').value), free_until:Number($('default-until').value)};
  }
  async function loadDefaults() {
    const data = await json('/api/storage/default-rule');
    const rule = data.rule;
    $('default-ratio').value = rule.ratio;
    $('default-days').value = rule.seed_seconds / 86400;
    $('default-operator').value = rule.seed_operator;
    $('default-trigger').value = rule.trigger_mode;
    $('default-below').value = rule.free_below;
    $('default-until').value = rule.free_until;
    $('default-status').textContent = data.sync_configured ? 'Partagée avec les instances fédérées.' : 'Enregistrée sur cette instance ; fédération non configurée.';
    $('default-space-thresholds').hidden = rule.trigger_mode !== 'pressure';
  }
  function reviewSelection() {
    const body = $('storage-selection-summary'); body.replaceChildren();
    const amount = preview.ready.reduce((sum, item) => sum + item.size, 0);
    body.append(node('p', `${preview.ready.length} éligible(s), ${preview.blocked.length} bloqué(s) · ${size(amount)} de fichiers sélectionnés (espace réellement libéré variable).`));
    const list = node('ul');
    preview.ready.forEach(item => list.append(node('li', `${item.name} — ${size(item.size)} — ${item.mode === 'torrent' ? item.torrent_count + ' torrent(s) associés' : 'fichier local'}`)));
    preview.blocked.forEach(item => list.append(node('li', `${item.id} — BLOQUÉ : ${item.reason}`)));
    body.append(list);
    if (preview.blocked.length) body.append(node('p', 'Retirez les éléments bloqués de la sélection avant de continuer.'));
    $('storage-selection-confirm').value = '';
    $('storage-selection-confirm').placeholder = `SUPPRIMER ${preview.ready.length}`;
    $('storage-selection-delete').disabled = true;
    $('storage-selection-dialog').showModal();
  }
  document.addEventListener('DOMContentLoaded', () => {
    displayMode();
    $('storage-layout').onclick = () => { layout = layout === 'list' ? 'gallery' : 'list'; localStorage.setItem('minivid_storage_layout', layout); displayMode(); };
    $('storage-width').onclick = () => { width = ({standard:'wide', wide:'full', full:'standard'})[width]; localStorage.setItem('minivid_storage_width', width); displayMode(); };
    document.querySelectorAll('#storage-sort,#storage-filter').forEach(el => el.addEventListener('change', () => { page = 1; loadStorage().catch(error => alert(error.message)); }));
    $('storage-prev').onclick = () => { --page; loadStorage().catch(error => alert(error.message)); };
    $('storage-next').onclick = () => { ++page; loadStorage().catch(error => alert(error.message)); };
    $('storage-select-page').onchange = event => {
      if (event.target.checked && new Set([...selected, ...lastResult.items.map(item => item.id)]).size > 100) {
        selectionStatus(); alert('Sélection limitée à 100 médias.'); return;
      }
      lastResult?.items.forEach(item => { if (event.target.checked) selected.add(item.id); else selected.delete(item.id); });
      document.querySelectorAll('input[data-storage-id]').forEach(box => { box.checked = selected.has(box.dataset.storageId); });
      selectionStatus();
    };
    $('storage-clear-selection').onclick = () => { selected.clear(); document.querySelectorAll('input[data-storage-id]').forEach(box => { box.checked = false; }); selectionStatus(); };
    $('storage-preview-selection').onclick = async () => {
      try { preview = await post('/api/storage/selection/preview', {items:[...selected]}); reviewSelection(); }
      catch (error) { alert('Prévisualisation refusée : ' + error.message); }
    };
    $('storage-selection-confirm').oninput = () => {
      $('storage-selection-delete').disabled = !preview?.ready.length || !!preview.blocked.length ||
        $('storage-selection-confirm').value !== `SUPPRIMER ${preview.ready.length}`;
    };
    $('storage-selection-cancel').onclick = () => $('storage-selection-dialog').close();
    $('storage-selection-delete').onclick = async () => {
      const button = $('storage-selection-delete'); button.disabled = true;
      try {
        const result = await post('/api/storage/selection/delete',
          {items:preview.ready.map(item => ({id:item.id, identity:item.identity})), confirmation:$('storage-selection-confirm').value});
        result.deleted.forEach(id => selected.delete(id));
        $('storage-selection-dialog').close(); await loadStorage();
      } catch (error) {
        // The server can report partial completion; refresh before another action.
        $('storage-selection-dialog').close(); selected.clear(); await loadStorage();
        alert('Suppression interrompue : ' + error.message + '. Vérifiez la liste avant de réessayer.');
      }
    };
    $('scan-storage').onclick = async () => {
      const button = $('scan-storage'); button.disabled = true;
      try {
        await json('/api/storage/scan', {method:'POST'});
        const timer = setInterval(async () => {
          try { await loadStorage(); if (!lastResult.scan.running) { clearInterval(timer); button.disabled = false; } }
          catch (error) { clearInterval(timer); button.disabled = false; alert(error.message); }
        }, 2500);
      } catch (error) { button.disabled = false; alert(error.message); }
    };
    $('automation-here').onclick = event => { $('automation-owner').value = event.currentTarget.dataset.instance || ''; };
    $('automation-save').onclick = async () => {
      try { await post('/api/storage/automation', {enabled:$('automation-enabled').checked, owner_id:$('automation-owner').value}); await loadAutomation(); }
      catch (error) { $('automation-status').textContent = 'Enregistrement refusé : ' + error.message; }
    };
    $('default-trigger').onchange = () => { $('default-space-thresholds').hidden = $('default-trigger').value !== 'pressure'; };
    $('default-save').onclick = async () => {
      try { await post('/api/storage/default-rule', defaultPayload()); await loadDefaults(); $('default-status').textContent = 'Règle par défaut enregistrée.'; }
      catch (error) { $('default-status').textContent = 'Enregistrement refusé : ' + error.message; }
    };
    loadStorage().catch(error => { $('storage-scan-status').textContent = error.message; });
    loadAutomation().catch(error => { $('automation-status').textContent = error.message; });
    loadDefaults().catch(error => { $('default-status').textContent = error.message; });
  });
})();

/* Storage review: local display preferences, server-side policy and deletion checks. */
(() => {
  const $ = id => document.getElementById(id);
  const selected = new Set();
  let page = 1;
  let lastResult = null;
  let preview = null;
  let scanTimer = null;
  let layout = localStorage.getItem('minivid_storage_layout') === 'gallery' ? 'gallery' : 'list';
  let width = ['standard', 'wide', 'full'].includes(localStorage.getItem('minivid_storage_width'))
    ? localStorage.getItem('minivid_storage_width') : 'standard';
  let storageSection = ['duplicates', 'cleanup'].includes(localStorage.getItem('minivid_storage_section'))
    ? localStorage.getItem('minivid_storage_section') : 'duplicates';
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
    const raw = await response.text();
    let data;
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch (_) {
      throw new Error(`Erreur serveur HTTP ${response.status} : réponse non JSON`);
    }
    if (!response.ok || !data.ok) throw new Error(data.error || `Erreur HTTP ${response.status}`);
    return data;
  }
  const post = (url, data) => json(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});

  function setStorageSection(section) {
    storageSection = section === 'cleanup' ? 'cleanup' : 'duplicates';
    localStorage.setItem('minivid_storage_section', storageSection);

    document.querySelectorAll('[data-storage-section]').forEach(button => {
      const active = button.dataset.storageSection === storageSection;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });

    $('storage-panel-duplicates').hidden = storageSection !== 'duplicates';
    $('storage-panel-cleanup').hidden = storageSection !== 'cleanup';
  }

  function pathLabel(value) {
    const text = value || 'Chemin indisponible';
    const item = node('code', text, 'storage-copy-path');
    item.title = text;
    return item;
  }

  function duplicateOrigin(file) {
    const wrap = node('div', null, 'storage-copy-badges');
    wrap.append(storageOriginBadge(file));

    if (file.cross_seed) {
      const note = node('span', 'Torrent tagué cross-seed', 'storage-cross-seed-note');
      note.title = 'Tag du torrent associé. Cela ne signifie pas que le fichier est un hardlink.';
      wrap.append(note);
    }

    return wrap;
  }

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
  function storageOriginBadge(file) {
    const cls = file.management === 'torrent' ? 'torrent' : file.management === 'unknown' ? 'unknown' : 'local';
    return node('span', file.management_label || 'Fichier local', 'storage-origin-badge ' + cls);
  }
  function renderStorageOverview(result) {
    const sources=$('storage-sources'), volumes=$('storage-volumes'); sources.replaceChildren(); volumes.replaceChildren();
    const indexed=(result.sources||[]).reduce((sum,x)=>sum+Number(x.indexed_count||0),0);
    $('storage-source-count').textContent=`${(result.sources||[]).length} source(s) · ${indexed} vidéos`;
    (result.sources||[]).forEach(source=>{const card=node('div',null,'storage-source-item'),top=node('div',null,'storage-source-top'); top.append(node('strong',source.name),node('span',`${source.indexed_count||0} vidéo(s)`,'storage-count-pill'));
      const info=node('div',null,'storage-source-meta'); info.append(node('span',source.torrent_configured?`Client configuré : ${source.client_name||source.client_type||'BitTorrent'}`:'Aucun client BitTorrent associé à la source','storage-origin-badge '+(source.torrent_configured?'torrent':'local')));
      info.append(node('span',source.read_only===true?'Montage lecture seule':source.read_only===false?'Montage accessible en écriture':'Mode d’accès indéterminé','storage-source-access'));
      card.append(top,node('code',source.path||'','storage-path'),info); sources.append(card);});
    (result.volumes||[]).forEach((volume,index)=>{const card=node('div',null,'storage-volume-item'),free=volume.total?Number(volume.free)/Number(volume.total)*100:0,names=(volume.sources||[]).map(x=>x.name).join(' + ');
      card.append(node('strong',names||`Volume ${index+1}`),node('span',`${size(volume.free)} libres sur ${size(volume.total)} · ${free.toFixed(1)} %`,'storage-volume-space'));
      const bar=node('div',null,'storage-space-bar'),fill=node('i'); fill.style.width=`${Math.max(0,Math.min(100,free))}%`; bar.append(fill); card.append(bar); volumes.append(card);});
  }
  function syncScanUi(scan) {
    const running=!!scan?.running,button=$('scan-storage'),progress=$('storage-scan-progress'),percent=Number(scan?.progress||0); button.disabled=running; button.textContent=running?'Analyse en cours…':'Analyser les doublons'; progress.value=Math.max(0,Math.min(100,percent));
    const current=Number(scan?.current||0),total=Number(scan?.total||0),countText=total?` · ${current}/${total}`:''; $('storage-scan-status').textContent=scan?.message||'Analyse à lancer.';
    $('storage-scan-detail').textContent=running?`${percent} %${countText}${scan?.phase?' · '+scan.phase:''}`:(scan?.phase==='error'?'Le dernier scan s’est terminé sur une erreur.':percent===100?'Dernière analyse terminée.':'');
    if(running&&!scanTimer){scanTimer=setInterval(()=>loadStorage().catch(error=>{clearInterval(scanTimer);scanTimer=null;button.disabled=false;$('storage-scan-status').textContent=error.message;}),1500);} else if(!running&&scanTimer){clearInterval(scanTimer);scanTimer=null;}
  }
  function appendDuplicateFile(list, file, digest, index) {
    const li = node('li', null, 'storage-copy-item');
    const main = node('div', null, 'storage-copy-main');
    const keep = document.createElement('input');
    keep.type = 'radio';
    keep.name = 'keep-' + digest;
    keep.value = file.id;
    keep.checked = index === 0;

    const keepLabel = node('span', 'Garder', 'storage-keep-label');
    const link = node('a', file.name || file.id, 'storage-copy-name');
    link.href = '/watch/' + encodeURIComponent(file.id);
    link.title = file.name || file.id;

    main.append(keep, keepLabel, link);

    const details = node('div', null, 'storage-copy-details');
    details.append(
      node('span', file.root_name || 'Source inconnue', 'storage-source-name'),
      pathLabel(file.path || file.relative_path),
      duplicateOrigin(file)
    );

    li.append(main, details);
    list.append(li);
  }

  function duplicateDetails(summaryText, className = '') {
    const details = node('details', null, `storage-duplicate-group ${className}`.trim());
    const summary = node('summary', null, 'storage-duplicate-summary');
    summary.append(
      node('span', summaryText, 'storage-duplicate-summary-title'),
      node('span', 'Afficher', 'storage-duplicate-toggle')
    );
    details.append(summary);
    details.addEventListener('toggle', () => {
      const toggle = details.querySelector('.storage-duplicate-toggle');
      if (toggle) toggle.textContent = details.open ? 'Replier' : 'Afficher';
    });
    return details;
  }

  function renderCopies(result) {
    const copies = $('storage-copies');
    copies.replaceChildren();

    $('storage-duplicates-count').textContent = String((result.copies || []).length);
    $('storage-cleanup-count').textContent = String(result.count || 0);

    if (!result.copies.length) {
      copies.append(node('p', 'Aucune copie physique vérifiée.', 'meta'));
    }

    result.copies.forEach(group => {
      const files = group.files || group.items.map(id => ({
        id,
        name: id,
        management: 'unknown',
        management_label: 'Informations non disponibles'
      }));

      const wrap = duplicateDetails(
        `${group.items.length} copies · jusqu’à ${size(group.estimated_bytes)} récupérables`
      );

      const body = node('div', null, 'storage-duplicate-body');
      const list = node('ul', null, 'storage-copy-list');
      files.forEach((file, index) => appendDuplicateFile(list, file, group.digest, index));
      body.append(list);

      if (result.admin) {
        const button = node('button', 'Supprimer les autres copies', 'btn btn-danger');
        button.onclick = async () => {
          const keep = wrap.querySelector('input:checked')?.value;
          const kept = files.find(file => file.id === keep);
          if (!keep) return;

          if (!confirm(
            `Conserver ${kept?.name || keep} et supprimer les autres copies ? ` +
            `Les contrôles serveur restent appliqués.`
          )) return;

          button.disabled = true;
          try {
            await post('/api/storage/duplicates/delete', {
              digest: group.digest,
              keep,
              confirmation: 'SUPPRIMER'
            });
            await loadStorage();
          } catch (error) {
            alert('Suppression refusée : ' + error.message);
            button.disabled = false;
          }
        };
        body.append(button);
      }

      wrap.append(body);
      copies.append(wrap);
    });

    const links = $('storage-links');
    links.replaceChildren();

    if (!result.links.length) {
      links.append(node('p', 'Aucun lien physique partagé dans les sources.', 'meta'));
    }

    result.links.forEach(group => {
      const wrap = duplicateDetails(
        `${group.items.length} chemins · même fichier physique · aucune copie supplémentaire`,
        'storage-hardlink-group'
      );
      const body = node('div', null, 'storage-duplicate-body');
      const list = node('ul', null, 'storage-copy-list');

      (group.files || []).forEach(file => {
        const li = node('li', null, 'storage-copy-item');
        const link = node('a', file.name || file.id, 'storage-copy-name');
        link.href = '/watch/' + encodeURIComponent(file.id);
        link.title = file.name || file.id;

        const details = node('div', null, 'storage-copy-details');
        details.append(
          node('span', file.root_name || 'Source inconnue', 'storage-source-name'),
          pathLabel(file.path || file.relative_path),
          duplicateOrigin(file)
        );

        li.append(link, details);
        list.append(li);
      });

      body.append(list);
      wrap.append(body);
      links.append(wrap);
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
    const query=new URLSearchParams({filter:$('storage-filter').value,sort:$('storage-sort').value,page});const result=await json('/api/storage?'+query);lastResult=result;renderStorageOverview(result);syncScanUi(result.scan||{});renderCopies(result);renderItems(result.items,result.admin);
    $('storage-total').textContent=`(${result.count})`;$('storage-page').textContent=`${page} / ${Math.max(1,Math.ceil(result.count/100))}`;$('storage-prev').disabled=page<=1;$('storage-next').disabled=page*100>=result.count;$('storage-select-page').disabled=!result.admin||!result.items.length;selectionStatus();displayMode();
  }
  async function loadAutomation() {
    const data=await json('/api/storage/automation');$('automation-enabled').checked=!!data.settings.enabled;$('automation-owner').value=data.settings.owner_id||'';$('automation-here').dataset.instance=data.instance_id;const list=$('automation-sources');list.replaceChildren();const selected=new Set((data.cleanup_roots||[]).map(Number));
    (data.sources||[]).forEach(source=>{const label=node('label',null,'automation-source-item'),box=document.createElement('input');box.type='checkbox';box.value=String(source.root);box.checked=selected.has(Number(source.root));box.disabled=!source.eligible;label.append(box,node('span',`${source.name} (${source.path})${source.client_name?' · '+source.client_name:''}${source.eligible?'':' · non éligible au nettoyage auto'}`));list.append(label);});
    $('automation-status').textContent=data.active?'Actif sur cette instance.':data.sync_configured?'Suspendu ou exécuté par une autre instance.':'Synchronisation non configurée : activation impossible.';$('federation-status').textContent=`Fédération : ${data.sync_configured?data.peer_count+' pair(s) configuré(s)':'non configurée'} · Identifiant de cette instance : ${data.instance_id}`;
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
    setStorageSection(storageSection);
    document.querySelectorAll('[data-storage-section]').forEach(button => {
      button.addEventListener('click', () => setStorageSection(button.dataset.storageSection));
    });
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
      try { await json('/api/storage/scan', {method:'POST'}); await loadStorage(); }
      catch (error) { button.disabled = false; alert(error.message); }
    };
    $('automation-here').onclick = event => { $('automation-owner').value = event.currentTarget.dataset.instance || ''; };
    $('automation-save').onclick = async () => {
      try { const cleanupRoots=[...document.querySelectorAll('#automation-sources input:checked')].map(box=>Number(box.value)); await post('/api/storage/automation', {enabled:$('automation-enabled').checked, owner_id:$('automation-owner').value, cleanup_roots:cleanupRoots}); await loadAutomation(); }
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

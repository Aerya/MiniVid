(() => {
  const t = value => window.MiniVidI18n?.t(value) || value;
  const make = (tag, text) => { const node = document.createElement(tag); if (text) node.textContent = text; return node; };
  const size = bytes => { let value = bytes, unit = 0; while (value >= 1024 && unit < 4) { value /= 1024; unit++; } return value.toFixed(unit ? 1 : 0) + ' ' + ['o','Ko','Mo','Go','To'][unit]; };
  const reasons = {
    suppression_desactivee: 'Suppression désactivée dans Maintenance',
    integration_torrent_desactivee: 'Intégration BitTorrent désactivée',
    client_non_configure: 'Aucun client BitTorrent associé à cette source',
    suppression_interdite_pour_cette_source: 'Suppression non autorisée pour cette source',
    confirmation_invalide: 'Recopie exactement le nom du dossier pour confirmer.',
    authenticated_admin_required: 'Connexion administrateur requise',
  };
  const reason = code => t(reasons[code] || code);
  async function api(path, data) {
    const response = await fetch(path, {method: data === undefined ? 'GET' : 'POST', credentials:'same-origin',
      headers: data === undefined ? {} : {'Content-Type':'application/json'}, body: data === undefined ? undefined : JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok || !result.ok) throw Object.assign(new Error(result.error || 'Action impossible'), {result});
    return result;
  }
  async function folderDeletion(button) {
    button.disabled = true;
    const dialog = make('dialog'); dialog.className = 'resume-actions-dialog';
    const title = make('h2', 'Supprimer ce dossier ?'); title.id = 'folder-delete-title';
    dialog.setAttribute('aria-labelledby', title.id);
    const status = make('p', 'Lecture des informations…'); status.setAttribute('role','status');
    const close = make('button', 'Fermer'); close.type = 'button'; close.className = 'btn'; close.onclick = () => dialog.close();
    dialog.append(title, status, close); document.body.append(dialog);
    dialog.addEventListener('close', () => { dialog.remove(); button.disabled = false; }); dialog.showModal();
    const target = {root: button.dataset.root, dir: button.dataset.dir};
    try {
      const info = await api('/api/folder/management?' + new URLSearchParams(target));
      if (!dialog.isConnected) return;
      const name = make('p'); name.append(make('strong', info.dir));
      const list = make('ul');
      for (const source of info.sources) {
        const line = make('li', `${source.root_name} · ${source.video_count} vidéo(s) · ${size(source.size)}` + (source.extra_files ? ` · ${source.extra_files} fichier(s) annexe(s)` : ''));
        const detail = source.blocked ? reason(source.blocked) : (source.delete_mode === 'torrent'
          ? 'Torrents associés supprimés avec leurs données ; les autres fichiers restent si le client ne les retire pas.'
          : 'Dossier entier supprimé, fichiers annexes compris.');
        line.append(make('br'), make('small', detail));
        list.append(line);
      }
      const favorites = info.sources.reduce((total, source) => total + source.favorites, 0);
      const warning = make('p', favorites ? 'Les favoris de ce dossier seront aussi supprimés.' : ''); warning.hidden = !favorites;
      const confirmLabel = make('label', 'Pour confirmer, recopie le nom du dossier :');
      const confirmation = make('input'); confirmation.type = 'text'; confirmation.autocomplete = 'off'; confirmation.setAttribute('aria-label','Nom du dossier à confirmer');
      confirmLabel.append(confirmation);
      const save = make('button', 'Supprimer le dossier'); save.type = 'button'; save.className = 'btn';
      const footer = make('footer'); footer.append(save, close);
      status.textContent = '';
      confirmLabel.hidden = save.hidden = !info.can_delete;
      dialog.replaceChildren(title, name, list, warning, confirmLabel, status, footer);
      save.onclick = async () => {
        save.disabled = true;
        try {
          if (confirmation.value !== info.name) throw new Error('Recopie exactement le nom du dossier pour confirmer.');
          status.textContent = 'Suppression en cours…';
          await api('/api/folder/delete', {...target, confirmation: confirmation.value});
          try { localStorage.setItem('minivid_reading_changed', String(Date.now())); } catch (_) {}
          location.href = button.dataset.parent;
        } catch (error) {
          const done = error.result?.deleted?.length;
          status.textContent = reason(error.message) + (done ? ` · ${done} vidéo(s) déjà supprimée(s)` : '');
          save.disabled = false;
        }
      };
    } catch (error) { status.textContent = reason(error.message); }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-folder-delete]');
    if (button) folderDeletion(button);
  });
})();

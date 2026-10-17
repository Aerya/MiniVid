(() => {
  const make = (tag, text) => { const node = document.createElement(tag); if (text) node.textContent = text; return node; };
  async function api(path, data) {
    const response = await fetch(path, {method: data === undefined ? 'GET' : 'POST', credentials:'same-origin',
      headers: data === undefined ? {} : {'Content-Type':'application/json'}, body: data === undefined ? undefined : JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Action impossible');
    return result;
  }
  async function deletionOptions(button) {
    button.disabled = true;
    const dialog = make('dialog'); dialog.className = 'resume-actions-dialog';
    const title = make('h2', 'Supprimer cette vidéo ?'); title.id = 'resume-delete-title';
    dialog.setAttribute('aria-labelledby', title.id);
    const status = make('p', 'Lecture des informations…'); status.setAttribute('role','status');
    const close = make('button', 'Fermer'); close.type = 'button'; close.className = 'btn'; close.onclick = () => dialog.close();
    dialog.append(title, status, close); document.body.append(dialog);
    dialog.addEventListener('close', () => { dialog.remove(); button.disabled = false; }); dialog.showModal();
    const id = button.dataset.resumeDelete;
    try {
      const info = await api('/api/media/'+encodeURIComponent(id)+'/management');
      if (!dialog.isConnected) return;
      const name = make('p', info.name);
      const choiceLabel = make('label', 'Action');
      const choice = make('select'); choice.setAttribute('aria-label','Action');
      const options = [['keep','Garder le fichier et retirer de la reprise']];
      if(info.can_delete) options.push(['delete','Supprimer le fichier maintenant']);
      const torrent = info.delete_mode === 'torrent' && info.torrents?.length;
      if(torrent && info.can_delete) options.push(['seed','Continuer le seed, puis autoriser le nettoyage']);
      for(const [value,label] of options){const option=make('option',label);option.value=value;choice.append(option);}
      choiceLabel.append(choice);
      const delay = make('div'); delay.hidden = true;
      const daysLabel = make('label', 'Temps de seed minimum total');
      const days = make('input'); days.type='number';days.min='1';days.max='3650';days.value='14';days.setAttribute('aria-label','Durée de seed');
      const unit = make('select');unit.setAttribute('aria-label','Unité');
      for(const [value,label] of [[1,'jours'],[7,'semaines']]){const option=make('option',label);option.value=value;unit.append(option);}
      daysLabel.append(days,unit); delay.append(daysLabel);
      const explanation=make('p','Chaque torrent associé doit atteindre cette durée réelle de seed, y compris les cross-seeds. Les favoris restent protégés.');delay.append(explanation);
      const warning=make('p'); delay.append(warning);
      const storage=make('a','Voir le nettoyage dans Stockage →');storage.href='/storage';delay.append(storage);
      const confirmLabel=make('label','Pour supprimer maintenant, recopie le nom du fichier :');confirmLabel.hidden=true;
      const confirmation=make('input');confirmation.type='text';confirmation.autocomplete='off';confirmation.setAttribute('aria-label','Nom du fichier à confirmer');confirmLabel.append(confirmation);
      const save=make('button','Valider');save.type='button';save.className='btn';
      const footer=make('footer');footer.append(save,close);
      dialog.replaceChildren(title,name,choiceLabel,delay,confirmLabel,status,footer);
      const rule = torrent ? await api('/api/storage/rule/'+encodeURIComponent(id)) : null;
      if(!dialog.isConnected)return;
      warning.textContent=rule?.automation_active ? 'Le nettoyage automatique est actif. Les protections et vérifications habituelles restent appliquées.' : 'Le nettoyage automatique est inactif : cette règle sera enregistrée, mais aucun fichier ne sera effacé automatiquement. Active-le dans Stockage ou supprime manuellement après le délai.';
      const update=()=>{delay.hidden=choice.value!=='seed';confirmLabel.hidden=choice.value!=='delete';status.textContent=choice.value==='delete'?(torrent?'Suppression définitive du fichier et de ses torrents associés.':'Suppression définitive du fichier.'):'Le fichier continue à être conservé.';};
      choice.onchange=update;update();
      save.onclick=async()=>{
        save.disabled=true;
        try {
          if(choice.value==='delete') {
            if(confirmation.value!==info.name)throw new Error('Recopie exactement le nom du fichier pour confirmer.');
            await api('/api/media/'+encodeURIComponent(id)+'/delete',{confirmation:confirmation.value});
          } else {
            if(choice.value==='seed') {
              const duration=Number(days.value)*Number(unit.value);
              if(!Number.isFinite(duration)||duration<1||duration>3650)throw new Error('Choisis une durée entre 1 et 3650 jours.');
              const saved=await api('/api/storage/rule/'+encodeURIComponent(id),{mode:'candidate',ratio:0,seed_seconds:Math.ceil(duration*86400),seed_operator:'and',trigger_mode:'immediate'});
              status.textContent='Règle enregistrée. '+saved.reason+(saved.automation_active?'':' · Nettoyage automatique inactif.');
            }
            await api('/api/resume/'+encodeURIComponent(id),{dismissed:true});
          }
          button.closest('.reading-item').hidden=true;
          if(choice.value==='seed') {save.hidden=true;choice.disabled=true;days.disabled=true;unit.disabled=true;}
          else dialog.close();
        } catch(error) {status.textContent=error.message;}
        finally {save.disabled=false;}
      };
    } catch(error) {status.textContent=error.message;}
  }
  document.addEventListener('click', async event => {
    const deletion = event.target.closest('[data-resume-delete]');
    if(deletion){await deletionOptions(deletion);return;}
    const button = event.target.closest('[data-resume-dismiss]');
    if (!button) return;
    button.disabled = true;
    const item = button.closest('.reading-item');
    const strip = item.parentElement;
    const setDismissed = async dismissed => {
      const response = await fetch('/api/resume/' + encodeURIComponent(button.dataset.resumeDismiss), {
        method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dismissed})
      });
      if (!response.ok) throw new Error('Impossible de modifier la liste. Réessaie.');
    };
    try {
      await setDismissed(true);
      item.hidden = true;
      const notice = document.createElement('div');
      notice.className = 'resume-notice'; notice.setAttribute('role', 'status');
      notice.append('Retirée de la reprise. Le fichier et la progression sont conservés. ');
      const undo = document.createElement('button'); undo.type = 'button'; undo.className = 'btn';
      undo.textContent = 'Annuler';
      undo.onclick = async () => {
        undo.disabled = true;
        try { await setDismissed(false); item.hidden = false; notice.remove(); }
        catch (error) { undo.disabled = false; undo.textContent = error.message; }
      };
      notice.append(undo); strip.before(notice);
    } catch (error) { button.textContent = error.message; }
    finally { button.disabled = false; }
  });
})();

(() => {
  const $ = id => document.getElementById(id);
  if (!$('tag-review-list')) return;
  const selected = new Set();
  let page = 1, pages = 1, generation = 0, timer;
  const view = $('tag-review-view'), search = $('tag-review-search'), apply = $('tag-review-apply');
  const node = (tag, text) => {const n = document.createElement(tag); if (text) n.textContent = text; return n;};
  function selectionChanged() {
    apply.disabled = !selected.size;
    apply.textContent = (view.value === 'ignored' ? 'Réafficher' : 'Ignorer') + ' la sélection' + (selected.size ? ' (' + selected.size + ')' : '');
  }
  async function request(data) {
    const url = '/api/banned_tags/review' + (data ? '' : '?' + new URLSearchParams({view:view.value,q:search.value,page}));
    const response = await fetch(url, {method:data?'POST':'GET',credentials:'same-origin',cache:'no-store',
      headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'Opération impossible');
    return result;
  }
  async function load(reset = false) {
    if (reset) {page=1;selected.clear();selectionChanged();}
    const turn = ++generation;
    try {
      const result = await request();
      if (turn !== generation) return;
      page=result.page;pages=result.pages;
      $('tag-review-summary').textContent = `${result.suggestions} proposition(s) technique(s) · ${result.ignored} tag(s) ignoré(s) · ${result.distinct} tag(s) repéré(s). Aucun choix automatique.`;
      const list=$('tag-review-list');list.replaceChildren();
      for(const item of result.items){
        const row=node('label');row.className='tag-review-row';
        const checkbox=node('input');checkbox.type='checkbox';checkbox.value=item.tag;checkbox.checked=selected.has(item.tag);
        checkbox.onchange=()=>{if(checkbox.checked)selected.add(item.tag);else selected.delete(item.tag);selectionChanged();};
        const text=node('span');text.append(node('strong',item.tag));if(item.reason)text.append(node('small',item.reason));
        const count=node('span',item.count+' vidéo(s)');count.className='tag-review-count';
        row.append(checkbox,text,count);list.append(row);
      }
      if(!result.items.length)list.append(node('p','Aucun tag dans cette vue.'));
      $('tag-review-page').textContent=`${result.total} tag(s) · page ${page}/${pages}`;
      $('tag-review-prev').disabled=page<=1;$('tag-review-next').disabled=page>=pages;
    }catch(error){if(turn===generation)$('tag-review-status').textContent=error.message;}
  }
  async function save(tags, action) {
    apply.disabled=true;
    try {
      await request({tags,action});selected.clear();selectionChanged();await load();
      $('tag-review-status').textContent = action === 'ignore' ? 'Tags ignorés. Les cartes et les nouvelles sélections utiliseront ce choix. Les métadonnées d’origine sont conservées.' : 'Tags réaffichés. Le compose reste inchangé.';
    }catch(error){$('tag-review-status').textContent=error.message;selectionChanged();}
  }
  apply.onclick=()=>save([...selected],view.value==='ignored'?'restore':'ignore');
  view.onchange=()=>load(true);
  search.oninput=()=>{clearTimeout(timer);generation++;timer=setTimeout(()=>load(true),250);};
  $('tag-review-refresh').onclick=()=>load(true);
  $('tag-review-prev').onclick=()=>{page--;load();};$('tag-review-next').onclick=()=>{page++;load();};
  $('tag-review-manual').onsubmit=async event=>{event.preventDefault();const input=$('tag-review-name');if(input.value.trim()){await save([input.value.trim()],'ignore');input.value='';}};
  load();
})();

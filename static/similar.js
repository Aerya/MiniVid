(() => {
  const sidebar=document.getElementById('watch-sidebar');
  if(!sidebar)return;
  const grid=document.getElementById('similar-grid'),main=document.getElementById('watchMain'),count=document.getElementById('sidebar-count');
  const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
  const t=text=>window.MiniVidI18n?.t(text)||text;
  const toggle=document.getElementById('similar-toggle');
  let collapsed=false;
  try{collapsed=localStorage.getItem('minivid_similar_collapsed')==='1';}catch{}
  function updateCollapse(){
    main.classList.toggle('sidebar-collapsed',collapsed);
    grid.hidden=collapsed;
    toggle.setAttribute('aria-expanded',String(!collapsed));
    const label=t(collapsed?'Déplier les vidéos similaires':'Replier les vidéos similaires');
    toggle.setAttribute('aria-label',label);toggle.title=label;
    toggle.firstElementChild.textContent=collapsed?'<':'>';
  }
  toggle.addEventListener('click',()=>{
    collapsed=!collapsed;updateCollapse();
    try{localStorage.setItem('minivid_similar_collapsed',collapsed?'1':'0');}catch{}
  });
  window.addEventListener('minivid:language',updateCollapse);
  updateCollapse();
  let generation=0;
  async function api(url,data){const r=await fetch(url,{method:data===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:data===undefined?{}:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});const j=await r.json();if(!r.ok||!j.ok)throw Error('Action indisponible');return j;}
  function size(bytes){const en=document.documentElement.lang==='en';return bytes>=1073741824?(bytes/1073741824).toFixed(1)+(en?' GB':' Go'):(bytes/1048576).toFixed(1)+(en?' MB':' Mo');}
  function card(video,personalized){
    const item=node('article',null,'side-card '+(video.played?'played':'unplayed'));item.dataset.vid=video.id;
    const back=new URLSearchParams(location.search).get('back')||'/browse';
    const href='/watch/'+encodeURIComponent(video.id)+'?back='+encodeURIComponent(back);
    const thumb=node('a',null,'side-thumb');thumb.href=href;
    const img=node('img');img.src='/thumb/'+encodeURIComponent(video.id)+'.jpg';img.alt='';img.loading='lazy';img.onerror=()=>{img.onerror=null;img.src='/static/placeholder.svg';};
    thumb.append(img,node('span',(video.ext||'').toUpperCase(),'side-ext'));
    if(video.played||video.reading_status==='in_progress')thumb.append(node('span',video.played?'Lue':'En cours','side-badge '+(video.played?'side-read':'side-progress')));
    const info=node('div',null,'side-info'),title=node('a',video.name,'side-title');title.href=href;title.title=video.name;title.translate=false;
    info.append(title,node('div',[size(video.size||0),video.res].filter(Boolean).join(' · '),'side-sub'));
    if(video.reasons?.length){const reasons=node('div',video.reasons.slice(0,2).join(' · '),'side-reasons');reasons.title=video.reasons.join(' · ');reasons.translate=false;info.append(reasons);}
    const actions=node('div',null,'side-actions'),favorite=node('button','♡','fav-btn'+(video.fav?' active':''));favorite.type='button';favorite.title=t('Favori');favorite.setAttribute('aria-label',t('Favori'));favorite.setAttribute('aria-pressed',String(!!video.fav));favorite.textContent=video.fav?'♥':'♡';
    favorite.onclick=async()=>{favorite.disabled=true;try{const next=!favorite.classList.contains('active');await api('/api/fav',{vid:video.id,fav:next});favorite.classList.toggle('active',next);favorite.setAttribute('aria-pressed',String(next));favorite.textContent=next?'♥':'♡';}catch{favorite.title=t('Erreur favori');}finally{favorite.disabled=false;}};
    actions.append(favorite);
    if(personalized){const opinions=node('div',null,'side-opinions');for(const[value,label,symbol]of[[1,'Ça m’intéresse','👍'],[-1,'Pas pour moi','👎']]){const button=node('button',symbol,'side-opinion');button.type='button';button.title=t(label);button.setAttribute('aria-label',t(label));button.setAttribute('aria-pressed',String(video.opinion===value));button.onclick=async()=>{for(const b of opinions.children)b.disabled=true;try{const snapshot=await api('/api/extensions/library');await api('/api/extension/v1/feedback',{video_id:video.id,videos:snapshot.videos,value:video.opinion===value?0:value});await load();}catch{let error=item.querySelector('.side-feedback-error');if(!error){error=node('span',null,'side-feedback-error');error.setAttribute('role','status');info.append(error);}error.textContent=t('Impossible d’enregistrer cet avis.');}finally{for(const b of opinions.children)b.disabled=false;}};opinions.append(button);}actions.append(opinions);}
    item.append(thumb,info,actions);return item;
  }
  async function load(){const turn=++generation;try{const data=await api('/api/similar/'+encodeURIComponent(sidebar.dataset.videoId));if(turn!==generation)return;const videos=data.videos||[];grid.replaceChildren(...videos.map(v=>card(v,data.source==='companion')));count.textContent=String(videos.length);sidebar.style.display=videos.length?'':'none';main.classList.toggle('has-sidebar',videos.length>0);}catch{/* Keep the last useful list on a transient connection failure. */}}
  window.addEventListener('minivid:recommendations-changed',load);
  load();
})();

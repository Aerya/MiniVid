(() => {
  const frame=document.getElementById('extension-frame');
  if(!frame)return;
  let metadataRequest=false;
  function send(){let video=null;try{video=frame.dataset.video?JSON.parse(frame.dataset.video):null;}catch{}frame.contentWindow?.postMessage({type:'minivid:extension:context',theme:frame.dataset.theme,accent:frame.dataset.accent,video},location.origin);}
  frame.addEventListener('load',send);
  window.addEventListener('message',async event=>{
    if(event.origin!==location.origin||event.source!==frame.contentWindow)return;
    if(event.data?.type==='minivid:extension:resize'){
      const height=Number(event.data.height);if(Number.isFinite(height))frame.style.height=Math.min(50000,Math.max(100,height+4))+'px';
    }
    if(event.data?.type==='minivid:extension:batch'){
      try{const r=await fetch('/api/extensions/batch',{method:'POST',credentials:'same-origin'});const data=await r.json();frame.contentWindow.postMessage({type:'minivid:extension:batch-started',...data},location.origin);}catch{frame.contentWindow.postMessage({type:'minivid:extension:batch-started',ok:false,error:'Compagnon inaccessible'},location.origin);}
    }
    if(event.data?.type==='minivid:extension:import')await fetch('/api/extensions/import',{method:'POST',credentials:'same-origin'});
    if(event.data?.type==='minivid:extension:metadata'&&!metadataRequest){
      let video;try{video=JSON.parse(frame.dataset.video);}catch{return;}
      if(event.data.id!==video.id)return;
      metadataRequest=true;
      try{await fetch('/api/extensions/metadata/'+encodeURIComponent(video.id),{method:'POST',credentials:'same-origin'});}finally{metadataRequest=false;}
    }
  });
})();

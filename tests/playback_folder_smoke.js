/* Run with: node tests/playback_folder_smoke.js */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const settle = () => new Promise(resolve => setImmediate(resolve));

class Element {
  constructor(tag = '') { this.tag = tag; this.children = []; this.listeners = {}; this.dataset = {}; this.isConnected = true; this.hidden = false; this.disabled = false; this.value = ''; }
  set textContent(value) { this.label = value; this.children = []; }
  get textContent() { return this.label || ''; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = [...items]; }
  setAttribute() {}
  addEventListener(event, callback) { this.listeners[event] = callback; }
  showModal() {}
  close() { this.listeners.close?.(); }
  remove() { this.isConnected = false; }
}
const descendants = node => [node, ...node.children.filter(item => item instanceof Element).flatMap(descendants)];
const pending = {ok:true, id:'persisted-job', status:'pending', remaining_videos:2, remaining_files:3};

async function folderScenario(reopen, loseResponse = false) {
  let click;
  const body = new Element();
  const document = {body, createElement: tag => new Element(tag), addEventListener: (event, cb) => { if (event === 'click') click = cb; }};
  const button = new Element();
  button.dataset = {root:'0', dir:'Pack', parent:'/browse'};
  const timers = [], requests = [];
  let active = reopen, polls = 0;
  const location = {href:''};
  const fetch = async (url, opts) => {
    requests.push({url, method:opts.method});
    if (url === '/api/folder/delete') {
      active = true;
      if (loseResponse) throw new Error('lost response');
      return {ok:true, json:async () => pending};
    }
    if (url.includes('id=persisted-job')) {
      if (++polls === 1) throw new Error('temporary network error');
      return {ok:true, json:async () => ({ok:true, id:'persisted-job', status:'completed'})};
    }
    if (url.startsWith('/api/folder/deletion')) return {ok:true, json:async () => active ? pending : {ok:true, status:'idle'}};
    return {ok:true, json:async () => ({ok:true, name:'Pack', dir:'Pack', can_delete:true, sources:[{root_name:'Tests', video_count:2, size:20, extra_files:1, favorites:0, delete_mode:'torrent'}]})};
  };
  vm.runInNewContext(fs.readFileSync(path.join(root,'static/folder-delete.js'),'utf8'), {
    document, window:{}, fetch, location, URLSearchParams, localStorage:{setItem(){}}, setTimeout: cb => timers.push(cb),
  });
  click({target:{closest:() => button}});
  await settle();
  const dialog = body.children[0];
  if (!reopen) {
    const input = descendants(dialog).find(item => item.tag === 'input');
    const save = descendants(dialog).find(item => item.textContent === 'Supprimer le dossier');
    input.value = 'Pack';
    save.onclick();
    await settle();
    assert.ok(save.disabled, 'destructive control remains disabled');
    assert.ok(save.hidden, 'pending deletion hides destructive control');
  }
  const status = descendants(dialog).find(item => item.tag === 'p' && item.textContent.includes('restante(s)'));
  assert.ok(status, 'remaining counts displayed');
  assert.equal(location.href, '', 'no premature navigation');
  timers.shift()();
  await settle();
  assert.ok(descendants(dialog).some(item => item.textContent.includes('Vérification momentanément indisponible')), 'poll failures are not deletion failures');
  timers.shift()(); // retry backoff
  await settle();
  timers.shift()(); // next observation
  await settle();
  assert.equal(location.href, '/browse', 'completion returns to parent');
  assert.equal(requests.filter(item => item.method === 'POST').length, reopen ? 0 : 1, 'never resend deletion');
}

async function seekScenario() {
  const listeners = {};
  const video = {currentTime:81, duration:100, paused:true, addEventListener:(event, cb) => { listeners[event] = cb; }};
  const readState = {dataset:{status:'unread'}};
  const readBtn = {classList:{toggle() {}}};
  const requests = [];
  const html = fs.readFileSync(path.join(root,'templates/watch.html'),'utf8');
  const start = html.indexOf("    const v = document.getElementById('v');");
  const end = html.indexOf('    loadMediaManagement();', start);
  vm.runInNewContext(html.slice(start, end), {
    document:{getElementById:id => id === 'v' ? video : null}, window:{addEventListener(){}}, VID:'test-video', readState, readBtn,
    localStorage:{setItem(){}}, fetch:async (url, opts) => {
      requests.push(JSON.parse(opts.body));
      return {json:async () => ({ok:true, played:true, reading_status:'read'})};
    },
  });
  listeners.seeked();
  await settle();
  assert.equal(requests[0].progress, 81, 'paused seek is saved immediately');
  assert.equal(requests[0].watched, 0, 'seeking does not invent watched time');
  assert.equal(readState.textContent, 'Lue', 'returned reading state updates player');
}

(async () => {
  await folderScenario(false);
  await folderScenario(true);
  await folderScenario(false, true);
  await seekScenario();
  console.log('Folder deletion: pending, reopen, polling errors, lost POST response OK; paused seek saved');
})().catch(error => { console.error(error); process.exitCode = 1; });

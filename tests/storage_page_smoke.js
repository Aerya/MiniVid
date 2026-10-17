/* Run with: node tests/storage_page_smoke.js */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'templates/storage.html'), 'utf8');
const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
const elements = new Map();

class Element {
  constructor() {
    this.children = [];
    this.listeners = {};
    this.dataset = {};
    this.classList = {add() {}, toggle() {}};
    this.value = '';
    this.hidden = false;
  }
  set textContent(value) { this.label = value; this.children = []; }
  get textContent() { return this.label || ''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
  setAttribute() {}
  addEventListener(event, callback) { this.listeners[event] = callback; }
}

const get = id => {
  if (!ids.has(id)) return null;
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
let ready;
const document = {
  getElementById: get,
  querySelector: selector => {
    if (selector !== '.storage-page' || !html.includes('class="container storage-page"')) return null;
    if (!elements.has('storage-root')) elements.set('storage-root', new Element());
    return elements.get('storage-root');
  },
  querySelectorAll: selector => selector === '#storage-sort,#storage-filter' ? [get('storage-sort'), get('storage-filter')] : [],
  createElement: () => new Element(),
  addEventListener: (event, listener) => { if (event === 'DOMContentLoaded') ready = listener; },
};

const requests = [];
let deferred = null;
const fetch = async url => {
  requests.push(url);
  if (deferred && url.startsWith('/api/storage?')) return new Promise(resolve => deferred.push(resolve));
  const result = url.startsWith('/api/storage?')
    ? {ok:true, admin:true, count:1, items:[{id:'video', name:'Vidéo test', size:1024, mtime:1700000000, policy:'none'}],
       mounts:[], copies:[], links:[], scan:{running:false, message:''}, scanned_at:0}
    : url === '/api/storage/automation'
      ? {ok:true, settings:{enabled:false, owner_id:''}, instance_id:'local', sync_configured:false, peer_count:0, active:false}
      : {ok:true, rule:{ratio:1, seed_seconds:86400, seed_operator:'and', trigger_mode:'pressure', free_below:15, free_until:20}};
  return {ok:true, text:async () => JSON.stringify(result)};
};

const values = new Map();
const localStorage = {
  getItem: key => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
};

vm.runInNewContext(fs.readFileSync(path.join(root, 'static/storage.js'), 'utf8'), {
  document, fetch, localStorage, URLSearchParams, alert: () => {}, setInterval, clearInterval,
});

(async () => {
  assert.equal(typeof ready, 'function');
  ready();
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.ok(requests.some(url => url.startsWith('/api/storage?')), 'inventory requested');
  assert.equal(get('storage-rows').children.length, 1, 'list row rendered');
  assert.equal(typeof get('storage-layout').onclick, 'function');
  assert.equal(typeof get('storage-width').onclick, 'function');
  get('storage-layout').onclick();
  assert.equal(get('storage-gallery').hidden, false, 'gallery displayed');
  get('storage-width').onclick();
  assert.equal(elements.get('storage-root').dataset.width, 'wide', 'width changed');
  // A slower previous sort response must never replace the current selection.
  deferred = [];
  get('storage-sort').value = 'oldest';
  get('storage-sort').listeners.change();
  get('storage-sort').value = 'size';
  get('storage-sort').listeners.change();
  assert.equal(deferred.length, 2);
  const reply = (name) => ({ok:true, text:async () => JSON.stringify({ok:true, admin:false, count:1,
    items:[{id:name, name, size:10}], sources:[], copies:[], links:[], scan:{running:false}})});
  deferred[1](reply('newest-response'));
  await new Promise(resolve => setTimeout(resolve, 0));
  const currentRow = get('storage-rows').children[0];
  deferred[0](reply('stale-response'));
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(get('storage-rows').children[0], currentRow, 'stale response ignored');
  assert.equal(get('storage-loading').textContent, '1 fichier(s) · liste à jour');
  console.log('Storage page: list, gallery and width controls OK');
})().catch(error => { console.error(error); process.exitCode = 1; });

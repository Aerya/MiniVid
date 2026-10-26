const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const settle = () => new Promise(resolve => setImmediate(resolve));
const script = fs.readFileSync(path.join(__dirname, '../static/topbar.js'), 'utf8');
(async () => {
  for (const pathname of ['/browse', '/home']) {
    const timers = [];
    let reloaded = 0, fail = false, responseOK = true;
    let scan = {ok:true, running:true, kind:'initial', indexed:0};
    const banner = {
      dataset:{count:'0'}, textContent:'Vérification en cours',
      replaceChildren(...children) { this.children = children; },
    };
    const href = `http://localhost${pathname}?q=test&sort=name&page=2#videos`;
    vm.runInNewContext(script, {
      document:{
        getElementById:id => id === 'library-initial-scan' ? banner : null,
        createElement:tag => ({tag}),
      },
      fetch:async () => {if(fail)throw new Error('offline');return {ok:responseOK,json:async () => scan};},
      location:{pathname, href, reload:() => reloaded++}, setTimeout:fn => timers.push(fn),
    });
    const [status, , refresh] = banner.children;
    const tick = async () => {assert.equal(timers.length, 1);timers.shift()();await settle();};
    await tick();
    assert.equal(refresh.hidden, true, 'no refresh needed for an unchanged library');
    fail = true;
    await tick();
    assert.equal(timers.length, 1, 'retry after a network error');
    fail = false;
    responseOK = false;
    await tick();
    assert.equal(timers.length, 1, 'retry after an HTTP error');
    responseOK = true;
    for (const count of [1, 4, 12]) {
      scan.indexed = count;
      await tick();
      assert.equal(reloaded, 0, 'indexing never interrupts browsing');
      assert.ok(status.textContent.includes(`: ${count}.`));
      assert.equal(refresh.hidden, false);
      assert.equal(refresh.href, href, 'manual refresh preserves filters and position');
    }
    scan.running = false;
    await tick();
    assert.ok(status.textContent.includes('terminée'));
    assert.equal(timers.length, 0, 'stop polling when the initial scan finishes');
    assert.equal(reloaded, 0, 'scan completion also leaves navigation untouched');
  }
  vm.runInNewContext(script, {
    document:{getElementById:() => null},
    setTimeout:() => assert.fail('no polling without an initial scan banner'),
  });
  console.log('Initial scan: non-disruptive progress, manual refresh, retries and completion OK');
})().catch(error => {console.error(error);process.exitCode=1;});

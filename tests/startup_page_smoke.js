const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const settle = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  const timers = [];
  let reloaded = 0, fail = false;
  let scan = {ok:true,running:true,kind:'initial',indexed:0};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/topbar.js'),'utf8'), {
    document:{getElementById:id => id === 'library-initial-scan' ? {dataset:{count:'0'}} : null},
    fetch:async () => {if(fail)throw new Error('offline');return {ok:true,json:async () => scan};},
    location:{reload:() => reloaded++}, setTimeout:fn => timers.push(fn),
  });
  timers.shift()(); await settle();
  assert.equal(reloaded,0,'do not reload a library that has not changed');
  fail = true;
  timers.shift()(); await settle();
  assert.equal(reloaded,0,'a network error does not reload or cancel observation');
  fail = false; scan.indexed = 1;
  timers.shift()(); await settle();
  assert.equal(reloaded,1,'show the first verified video without waiting for the whole scan');
  console.log('Initial scan: wait, network retry and progressive refresh OK');
})().catch(error => {console.error(error);process.exitCode=1;});

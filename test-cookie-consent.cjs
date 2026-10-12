const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('cookie-consent.js', 'utf8');
const key = 'ivancevic-cookie-consent';
function boot(initial, blocked = false) {
  const storage = new Map(initial ? [[key, initial]] : []);
  const events = {};
  const scripts = [];
  const deletes = [];
  const nodes = {};
  function node() {
    return { dataset: {}, hidden: false, checked: false, setAttribute() {}, appendChild() {}, focus() {}, addEventListener(type, cb) { this[type] = cb; }, contains() { return false; } };
  }
  const body = node();
  const document = { body, activeElement: body, documentElement: {lang: 'de'}, head: {appendChild(el) { scripts.push(el); }}, querySelector() { return body; }, querySelectorAll() { return []; }, createElement() { const el = node(); el.querySelector = selector => nodes[selector] ||= node(); return el; } };
  Object.defineProperty(document, 'cookie', {get() { return '_pk_id.2=x; other=y'; }, set(value) { deletes.push(value); }});
  const window = { addEventListener(type, cb) { events[type] = cb; } };
  let panel;
  body.appendChild = el => { if (el.className === 'cookie-panel') panel = el; };
  const timers = [];
  const sandbox = { document, window, location: {hostname:'www.ivancevicweb.com'}, localStorage: {getItem(k) { if (blocked) throw Error('blocked'); return storage.get(k) || null; }, setItem(k,v) { if (blocked) throw Error('blocked'); storage.set(k,v); }}, MutationObserver: class { observe() {} }, setTimeout(cb, delay) { timers.push({cb, delay}); return timers.length; }, clearTimeout() {}, Date };
  vm.runInNewContext(source, sandbox);
  return {window, storage, scripts, deletes, nodes, panel, events, timers, click(choice) { panel.click({target:{dataset:{choice}}}); }};
}
function stored(analytics, expired = false) {
  const timestamp = Date.now() - (expired ? 181 * 86400000 : 1000);
  return JSON.stringify({ version:1, analytics, timestamp, expires:timestamp + 180 * 86400000 });
}
const fresh = boot();
assert.equal(fresh.scripts.length, 0);
assert.equal(fresh.panel.hidden, false);
assert.equal(fresh.nodes.input.checked, false);
fresh.click('settings');
assert.equal(fresh.nodes['.cookie-details'].hidden, false);
fresh.click('save');
assert.equal(fresh.scripts.length, 0);
assert.equal(JSON.parse(fresh.storage.get(key)).analytics, false);
const accepted = boot();
accepted.click('accept');
assert.equal(accepted.scripts.length, 1);
assert.equal(accepted.scripts[0].src, 'https://matomo.ivancevicart.com/matomo.js');
assert.equal(accepted.window._paq[0][0], 'requireConsent');
assert.equal(accepted.window._paq.filter(cmd => cmd[0] === 'trackPageView').length, 1);
accepted.click('reject');
assert.equal(accepted.window._paq.at(-2)[0], 'forgetConsentGiven');
assert.equal(accepted.window._paq.at(-1)[0], 'deleteCookies');
assert(accepted.deletes.some(value => value.startsWith('_pk_id.2=;')));
assert(!accepted.deletes.some(value => value.startsWith('other=')));
accepted.click('accept');
assert.equal(accepted.scripts.length, 1);
assert.equal(accepted.window._paq.at(-1)[0], 'setConsentGiven');
assert.equal(boot(stored(true)).scripts.length, 1);
assert.equal(boot(stored(false)).scripts.length, 0);
assert.equal(boot(stored(true, true)).scripts.length, 0);
assert.equal(boot('{broken').scripts.length, 0);
assert.equal(boot(JSON.stringify({version:1, analytics:true, timestamp:Date.now(), expires:Infinity})).scripts.length, 0);
const unavailable = boot(null, true);
assert.equal(unavailable.scripts.length, 0);
unavailable.click('reject');
assert.equal(unavailable.panel.hidden, true);
accepted.storage.set(key, stored(false));
accepted.events.storage({key});
assert.equal(accepted.window._paq.at(-2)[0], 'forgetConsentGiven');
for (const name of ['index.html', 'projects.html', 'impressum.html', 'dataprotection.html', 'website-erstellung.html', 'website-wartung.html', 'seo-optimierung.html', 'google-unternehmensprofil.html']) {
  const html = fs.readFileSync(name, 'utf8');
  assert(html.includes('src="cookie-consent.js"'));
  assert(!/fonts\.google|cdnjs\.cloudflare|trackPageView/.test(html));
}
console.log('Consent checks passed: opt-in, rejection, withdrawal, saved choices, expiry, malformed/blocked storage, cross-tab changes and page integration.');

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('website-erstellung.html', 'utf8');
const elements = [...html.matchAll(/data-i18n="([^"]+)"[^>]*>([^<]*)</g)].map(match => ({ dataset: {i18n: match[1]}, textContent: match[2] }));
const images = [...html.matchAll(/data-i18n-alt="([^"]+)"/g)].map(match => ({dataset: {i18nAlt: match[1]}, alt: ''}));
const description = {content: ''};
const buttons = ['de', 'en'].map(lang => ({dataset: {lang}, classList: {toggle() {}}, addEventListener(type, cb) {this.click = cb;}}));
const document = {
  documentElement: {lang: 'de'}, body: {dataset: {page:'website'}},
  querySelectorAll(selector) {return selector === '[data-i18n]' ? elements : selector === '[data-i18n-alt]' ? images : selector === '.lang-toggle' ? buttons : [];},
  querySelector(selector) {return selector === 'meta[name="description"]' ? description : null;}
};
const store = new Map();
const context = {document, localStorage: {getItem(k) {return store.get(k);}, setItem(k,v) {store.set(k,v);}}, window: {addEventListener() {}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('lang.js','utf8'), context);
for (const lang of ['de','en','de']) {
  buttons.find(button => button.dataset.lang === lang).click();
  assert.equal(document.documentElement.lang, lang);
  for (const el of elements) {
    const expected = vm.runInContext(`translations.${lang}[${JSON.stringify(el.dataset.i18n)}]`,context);
    assert(expected, `Missing ${lang} translation: ${el.dataset.i18n}`);
    assert.equal(el.textContent, expected);
  }
  assert.equal(document.title, vm.runInContext(`translations.${lang}['website.metaTitle']`,context));
  assert.equal(description.content, vm.runInContext(`translations.${lang}['website.metaDescription']`,context));
  assert(images.every(image => image.alt));
}
assert.equal((html.match(/<h1\b/g)||[]).length,1);
assert(/^<!DOCTYPE html>\r?\n<html lang="de">/.test(html));
for (const key of ['business','seo']) {
  const homepage = fs.readFileSync('index.html','utf8');
  const pattern = new RegExp(`<p class="price" data-i18n="pricing\\.${key}\\.price">([^<]+)</p>`);
  assert.equal(html.match(pattern)[1], homepage.match(pattern)[1]);
}
assert(html.includes('src="cookie-consent.js"'));
assert(html.includes('href="projects.html#website-projekt"'));
assert(fs.readFileSync('sitemap.xml','utf8').includes('https://ivancevicweb.com/website-erstellung.html'));
console.log('Service page checks passed: complete DE/EN translations, title/description switching, image alternatives, one H1, unchanged package prices, portfolio link and sitemap.');

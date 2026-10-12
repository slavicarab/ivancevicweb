const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
for (const [filename, page, priceKeys] of [
  ['website-erstellung.html', 'website', ['business', 'seo']],
  ['website-wartung.html', 'maintenance', ['care']],
  ['seo-optimierung.html', 'seo', []]
]) {
const html = fs.readFileSync(filename, 'utf8');
const elements = [...html.matchAll(/data-i18n="([^"]+)"[^>]*>([^<]*)</g)].map(match => ({ dataset: {i18n: match[1]}, textContent: match[2] }));
const images = [...html.matchAll(/data-i18n-alt="([^"]+)"/g)].map(match => ({dataset: {i18nAlt: match[1]}, alt: ''}));
const description = {content: ''};
const buttons = ['de', 'en'].map(lang => ({dataset: {lang}, classList: {toggle() {}}, addEventListener(type, cb) {this.click = cb;}}));
const document = {
  documentElement: {lang: 'de'}, body: {dataset: {page}},
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
  assert.equal(document.title, vm.runInContext(`translations.${lang}['${page}.metaTitle']`,context));
  assert.equal(description.content, vm.runInContext(`translations.${lang}['${page}.metaDescription']`,context));
  for (const image of images) {
    const expected = vm.runInContext(`translations.${lang}[${JSON.stringify(image.dataset.i18nAlt)}]`,context);
    assert(expected, `Missing ${lang} alternative: ${image.dataset.i18nAlt}`);
    assert.equal(image.alt, expected);
  }
}
assert.equal((html.match(/<h1\b/g)||[]).length,1);
assert(/^<!DOCTYPE html>\r?\n<html lang="de">/.test(html));
for (const key of priceKeys) {
  const homepage = fs.readFileSync('index.html','utf8');
  const pattern = new RegExp(`<p class="price" data-i18n="pricing\\.${key}\\.price">([^<]+)</p>`);
  assert.equal(html.match(pattern)[1], homepage.match(pattern)[1]);
}
assert(html.includes('src="cookie-consent.js"'));
assert(html.includes(`rel="canonical" href="https://ivancevicweb.com/${filename}"`));
assert(fs.readFileSync('sitemap.xml','utf8').includes(`https://ivancevicweb.com/${filename}`));
if (page === 'website') assert(html.includes('href="projects.html#website-projekt"'));
if (page === 'maintenance') {
  assert(html.includes('<title>Website-Wartung &amp; Betreuung in Österreich | Ivancevic Web</title>'));
  assert(html.includes('>Website-Wartung &amp; Betreuung für kleine Unternehmen</h1>'));
  assert(!/wordpress|woocommerce|typo3|\bcms\b/i.test(html));
  for (const lang of ['de', 'en']) {
    const copy = vm.runInContext(`JSON.stringify(Object.fromEntries(Object.entries(translations.${lang}).filter(([key]) => key.startsWith('maintenance.'))))`, context);
    assert(!/wordpress|woocommerce|typo3|\bcms\b/i.test(copy));
  }
  for (const href of ['website-erstellung.html','index.html#preise','index.html#kontakt']) assert(html.includes(`href="${href}"`));
  assert(!html.includes('contact-topic-link'), 'Cross-page links must not pretend to preselect a form topic');
  assert(fs.readFileSync('index.html','utf8').includes('href="website-wartung.html" data-i18n="services.maintenance.more">Mehr erfahren</a>'));
}
if (page === 'seo') {
  const title = 'SEO-Optimierung für Unternehmen in Österreich | Ivancevic Web';
  const meta = 'Professionelle SEO-Optimierung für kleine Unternehmen in Österreich. Wir verbessern die Sichtbarkeit Ihrer Website bei Google – auch bei bestehenden Websites.';
  assert(html.includes(`<title>${title}</title>`));
  assert(html.includes(`name="description" content="${meta}"`));
  assert(html.includes('>SEO-Optimierung für kleine Unternehmen</h1>'));
  assert(html.includes('>Preis auf Anfrage</p>'));
  assert(!/\d+[.,]?\d*\s*€|€\s*\d/.test(html), 'No fixed SEO prices');
  for (const lang of ['de','en']) {
    const values = vm.runInContext(`Object.values(Object.fromEntries(Object.entries(translations.${lang}).filter(([key]) => key.startsWith('seo.'))))`,context);
    const copy = values.join(' ');
    assert(!/wordpress|woocommerce|typo3|\bcms\b|google ads|linkbuilding|link building|\d+[.,]?\d*\s*€|€\s*\d/i.test(copy));
    assert(lang === 'de' ? copy.includes('technischen Zugänge') && copy.includes('Plattform') && copy.includes('können nicht zugesagt werden') : copy.includes('technical access') && copy.includes('platform') && copy.includes('cannot be promised'));
  }
  for (const href of ['website-erstellung.html','website-wartung.html','index.html#kontakt']) assert(html.includes(`href="${href}"`));
  for (const id of ['warum','bestehende-websites','technik','on-page','analyse','betreuung','kosten','fragen','erstgespraech']) assert(html.includes(`id="${id}"`));
  assert(!html.includes('contact-topic-link'));
  assert(fs.readFileSync('index.html','utf8').includes('href="seo-optimierung.html" data-i18n="services.seo.more">Mehr erfahren</a>'));
  assert(html.includes('class="container hero-grid"') && html.includes('class="contact-grid"'));
  assert(html.includes('name="viewport" content="width=device-width, initial-scale=1.0"'));
}
console.log(`${filename}: translation, metadata, H1, pricing, canonical, links and sitemap checks passed.`);
}

const publicPages = ['index.html', 'website-erstellung.html', 'website-wartung.html', 'seo-optimierung.html', 'projects.html', 'impressum.html', 'dataprotection.html'];
const pages = new Map(publicPages.map(name => [name, fs.readFileSync(name, 'utf8')]));
const sitemap = fs.readFileSync('sitemap.xml', 'utf8');
const sitemapUrls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(match => match[1]);
const titles = [...pages.values()].map(html => html.match(/<title>([^<]+)<\/title>/)?.[1]);
assert.equal(new Set(titles).size, publicPages.length, 'Unique public-page SEO titles');
const descriptions = [...pages.values()].map(html => html.match(/name="description" content="([^"]+)"/)?.[1]).filter(Boolean);
assert.equal(new Set(descriptions).size, descriptions.length, 'Unique descriptions where present');
assert.equal(sitemapUrls.length, publicPages.length);
assert.equal(new Set(sitemapUrls).size, publicPages.length);
for (const [name, html] of pages) {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, `Duplicate IDs in ${name}`);
  const canonical = `https://ivancevicweb.com/${name === 'index.html' ? '' : name}`;
  assert(html.includes(`rel="canonical" href="${canonical}"`));
  assert(sitemapUrls.includes(canonical));
  for (const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    const url = match[1];
    if (/^[a-z][a-z0-9+.-]*:|^\/\//i.test(url)) continue;
    const [path, fragment] = url.split('#');
    const target = path || name;
    assert(fs.existsSync(target), `Missing asset/link: ${name} -> ${url}`);
    if (fragment) assert(pages.get(target)?.includes(`id="${fragment}"`), `Missing anchor: ${name} -> ${url}`);
  }
}
console.log('All public pages: internal links, anchors, assets, unique IDs and canonical/sitemap consistency passed.');

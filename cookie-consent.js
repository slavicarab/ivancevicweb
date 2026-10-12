(() => {
  'use strict';
  const KEY = 'ivancevic-cookie-consent';
  const VERSION = 1;
  const DAYS = 180;
  let loaded = false;
  let allowed = false;
  let expires = 0;
  let timer;
  let returnFocus;
  const copy = {
    en: {
      title: 'Your cookie preferences',
      text: 'We use necessary storage for your preferences. With your permission, self-hosted Matomo helps us understand website usage. Analytics data is hosted in Europe; we do not use Google Analytics or transfer it to the USA. You can use the website without analytics.',
      necessary: 'Necessary — always active',
      necessaryText: 'Remembers your cookie choice for 180 days and your selected language in this browser.',
      analytics: 'Optional analytics (Matomo)',
      analyticsText: 'Measures page visits and link interactions. Disabled until you consent. You can withdraw consent at any time.',
      accept: 'Accept all', reject: 'Reject optional', settings: 'Cookie settings', save: 'Save preferences', privacy: 'Privacy & cookie policy'
    },
    de: {
      title: 'Ihre Cookie-Einstellungen',
      text: 'Wir verwenden notwendigen Speicher für Ihre Einstellungen. Mit Ihrer Zustimmung hilft uns selbst gehostetes Matomo, die Nutzung der Website zu verstehen. Analysedaten werden in Europa gespeichert; wir verwenden kein Google Analytics und übertragen diese Daten nicht in die USA. Sie können die Website ohne Analyse nutzen.',
      necessary: 'Notwendig — immer aktiv',
      necessaryText: 'Speichert Ihre Cookie-Auswahl für 180 Tage und Ihre gewählte Sprache in diesem Browser.',
      analytics: 'Optionale Analyse (Matomo)',
      analyticsText: 'Misst Seitenaufrufe und Link-Interaktionen. Bis zu Ihrer Zustimmung deaktiviert. Sie können Ihre Einwilligung jederzeit widerrufen.',
      accept: 'Alle akzeptieren', reject: 'Optionale ablehnen', settings: 'Cookie-Einstellungen', save: 'Auswahl speichern', privacy: 'Datenschutz & Cookies'
    }
  };
  function read() {
    try {
      const value = JSON.parse(localStorage.getItem(KEY));
      if (value && value.version === VERSION && typeof value.analytics === 'boolean' &&
          Number.isFinite(value.timestamp) && value.timestamp <= Date.now() &&
          value.expires === value.timestamp + DAYS * 86400000 && value.expires > Date.now()) return value;
    } catch (_) { /* Storage unavailable: default to no consent. */ }
    return null;
  }
  function clearCookies() {
    const domains = ['', location.hostname];
    const parts = location.hostname.split('.');
    for (let i = 0; i < parts.length - 1; i++) domains.push('.' + parts.slice(i).join('.'));
    document.cookie.split(';').forEach(entry => {
      const name = entry.trim().split('=')[0];
      if (!/^(_pk_|mtm_consent|mtm_cookie_consent)/.test(name)) return;
      domains.forEach(domain => {
        document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax${domain ? '; Domain=' + domain : ''}`;
      });
    });
  }
  function tracking(enable) {
    allowed = enable;
    if (!enable) {
      if (loaded) window._paq.push(['forgetConsentGiven'], ['deleteCookies']);
      clearCookies();
      return;
    }
    if (loaded) {
      window._paq.push(['setConsentGiven']);
      return;
    }
    loaded = true;
    window._paq = window._paq || [];
    window._paq.push(
      ['requireConsent'],
      ['setTrackerUrl', 'https://matomo.ivancevicart.com/matomo.php'],
      ['setSiteId', '2'],
      ['setVisitorCookieTimeout', DAYS * 86400],
      ['setSessionCookieTimeout', 1800],
      ['setReferralCookieTimeout', DAYS * 86400],
      ['setConsentGiven'], ['trackPageView'], ['enableLinkTracking']
    );
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://matomo.ivancevicart.com/matomo.js';
    document.head.appendChild(script);
  }
  const panel = document.createElement('section');
  panel.className = 'cookie-panel';
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-labelledby', 'cookie-title');
  panel.innerHTML = `<h2 id="cookie-title" data-cookie="title"></h2><p data-cookie="text"></p>
    <a href="dataprotection.html#cookies" data-cookie="privacy"></a>
    <div class="cookie-details" hidden><h3 data-cookie="necessary"></h3><p data-cookie="necessaryText"></p>
    <label><input type="checkbox" id="cookie-analytics"> <span data-cookie="analytics"></span></label><p data-cookie="analyticsText"></p></div>
    <div class="cookie-actions"><button type="button" data-choice="accept" data-cookie="accept"></button><button type="button" data-choice="reject" data-cookie="reject"></button><button type="button" data-choice="settings" data-cookie="settings"></button><button type="button" data-choice="save" data-cookie="save" hidden></button></div>`;
  document.body.appendChild(panel);
  const details = panel.querySelector('.cookie-details');
  const checkbox = panel.querySelector('input');
  const settings = panel.querySelector('[data-choice="settings"]');
  const save = panel.querySelector('[data-choice="save"]');
  const opener = document.createElement('button');
  opener.type = 'button';
  opener.className = 'cookie-settings-link';
  opener.dataset.cookie = 'settings';
  (document.querySelector('.footer-links') || document.body).appendChild(opener);
  function translate() {
    const language = copy[document.documentElement.lang] || copy.en;
    document.querySelectorAll('[data-cookie]').forEach(el => { el.textContent = language[el.dataset.cookie]; });
  }
  function show(expand) {
    returnFocus = document.activeElement;
    checkbox.checked = allowed;
    panel.hidden = false;
    details.hidden = !expand;
    settings.hidden = expand;
    save.hidden = !expand;
  }
  function scheduleExpiry() {
    clearTimeout(timer);
    if (!expires) return;
    timer = setTimeout(() => {
      if (Date.now() >= expires) { expires = 0; tracking(false); show(false); }
      else scheduleExpiry();
    }, Math.min(expires - Date.now(), 2147483647));
  }
  function choose(analytics) {
    const timestamp = Date.now();
    expires = timestamp + DAYS * 86400000;
    try { localStorage.setItem(KEY, JSON.stringify({ version: VERSION, analytics, timestamp, expires })); } catch (_) {}
    tracking(analytics);
    scheduleExpiry();
    panel.hidden = true;
    if (panel.contains(document.activeElement)) (returnFocus && returnFocus !== document.body ? returnFocus : opener).focus();
  }
  panel.addEventListener('click', event => {
    const choice = event.target.dataset.choice;
    if (choice === 'accept') choose(true);
    if (choice === 'reject') choose(false);
    if (choice === 'save') choose(checkbox.checked);
    if (choice === 'settings') { show(true); checkbox.focus(); }
  });
  opener.addEventListener('click', () => { show(true); checkbox.focus(); });
  window.addEventListener('storage', event => {
    if (event.key !== KEY && event.key !== null) return;
    const value = read();
    expires = value ? value.expires : 0;
    tracking(Boolean(value && value.analytics));
    scheduleExpiry();
    if (value) panel.hidden = true; else show(false);
  });
  new MutationObserver(translate).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  translate();
  const existing = read();
  expires = existing ? existing.expires : 0;
  tracking(Boolean(existing && existing.analytics));
  panel.hidden = Boolean(existing);
  scheduleExpiry();
})();

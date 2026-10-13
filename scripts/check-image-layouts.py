"""Compare original and optimized pages locally with installed Chrome and Playwright."""
import functools
import hashlib
import json
import re
import sys
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'performance-review'
PAGES = sys.argv[1:] or ['index.html', 'projects.html', 'website-erstellung.html', 'website-wartung.html', 'seo-optimierung.html', 'google-unternehmensprofil.html']
VIEWPORTS = [(375, 812, 3), (390, 844, 2), (640, 900, 1), (900, 1000, 1), (901, 1000, 1), (1440, 1000, 1), (1440, 1000, 2)]

def original(name):
    return subprocess.check_output(['git', 'show', f'HEAD:{name}'], cwd=ROOT)

def validate_files():
    manifest = json.loads((ROOT / 'images/optimized/manifest.json').read_text())
    for name, spec in manifest.items():
        path = ROOT / f'{name}.png'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['source_sha256']
        assert path.read_bytes() == original(path.name), path.name
        if spec['lossless']:
            full = spec['variants'][-1]
            with Image.open(path) as before, Image.open(ROOT / full['path']) as after:
                assert ImageChops.difference(before.convert('RGB'), after.convert('RGB')).getbbox() is None
    for name in PAGES:
        before = original(name).decode('utf-8').replace('\r\n', '\n')
        after = (ROOT / name).read_text(encoding='utf-8')
        after = re.sub(r'<picture style="display: contents;"><source[^>]+>(<img[^>]+>)</picture>', r'\1', after)
        after = after.replace(' loading="eager"', '')
        after = after.replace(' style="position: relative;"', '')
        after = after.replace(' fetchpriority="high"', '')
        if name == 'projects.html':
            after = after.replace(' loading="lazy"', '')
        assert before == after, f'Unexpected non-image changes: {name}'
    for name in ['style.css', 'lang.js', 'cookie-consent.js', 'sitemap.xml', 'robots.txt']:
        assert (ROOT / name).read_bytes().replace(b'\r\n', b'\n') == original(name).replace(b'\r\n', b'\n'), name

def measure(page):
    return page.evaluate('''() => ({
      overflow: document.documentElement.scrollWidth > innerWidth,
      boxes: [...document.querySelectorAll('header, main, main section, footer, img, .cookie-panel, h1')].map(el => {
        const r = el.getBoundingClientRect(), c = getComputedStyle(el);
        return {tag: el.tagName, key: el.id || el.className || el.getAttribute('alt'),
          x: r.x, y: r.y + scrollY, width: r.width, height: r.height,
          crop: c.objectFit, position: c.objectPosition};
      }),
      images: [...document.images].map(el => ({src: el.currentSrc, loaded: el.complete && el.naturalWidth > 0,
        width: el.getBoundingClientRect().width, loading: el.loading, priority: el.fetchPriority})),
      lcp: window.lcpEntries || [],
      resources: performance.getEntriesByType('resource').filter(e => /\\.(png|webp)$/.test(e.name)).map(e => ({url:e.name,bytes:e.transferSize}))
    })''')

def run():
    validate_files()
    REPORT.mkdir(exist_ok=True)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
            for filename in PAGES:
                for width, height, dpr in VIEWPORTS:
                    measurements = {}
                    for mode in ['before', 'after']:
                        context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=dpr, is_mobile=width < 901)
                        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                        if mode == 'before':
                            context.route(f'{base}/{filename}', lambda route, request, name=filename: route.fulfill(body=original(name), content_type='text/html; charset=utf-8'))
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.add_init_script('''window.lcpEntries = []; new PerformanceObserver(list => {
                          for (const e of list.getEntries()) window.lcpEntries.push({time:e.startTime,
                            tag:e.element?.tagName, cls:e.element?.className, url:e.url, size:e.size});
                        }).observe({type:'largest-contentful-paint',buffered:true});''')
                        page.goto(f'{base}/{filename}', wait_until='networkidle')
                        page.wait_for_timeout(200)
                        initial = measure(page)
                        assert not errors, errors
                        assert page.locator('.cookie-panel').is_visible()
                        if filename == 'index.html' and width in [390, 1440] and dpr in [1, 2]:
                            page.screenshot(path=str(REPORT / f'home-{width}-{dpr}-{mode}-cookie.png'))
                        page.locator('[data-choice="settings"]').click()
                        assert page.locator('.cookie-details').is_visible()
                        page.locator('[data-choice="save"]').click()
                        assert not page.locator('.cookie-panel').is_visible()
                        page.locator('.cookie-settings-link').click()
                        page.locator('[data-choice="reject"]').click()
                        assert not page.locator('.cookie-panel').is_visible()
                        page.reload(wait_until='networkidle')
                        assert not page.locator('.cookie-panel').is_visible()
                        for img in page.locator('img').all():
                            img.scroll_into_view_if_needed()
                            img.evaluate('el => el.decode()')
                        page.evaluate('scrollTo({top:0,behavior:"instant"})')
                        page.wait_for_timeout(300)
                        final = measure(page)
                        assert all(img['loaded'] for img in final['images'])
                        if filename == 'index.html' and width in [390, 1440] and dpr in [1, 2]:
                            page.screenshot(path=str(REPORT / f'home-{width}-{dpr}-{mode}.png'), full_page=True)
                        measurements[mode] = {'initial': initial, 'final': final}
                        context.close()
                    before, after = measurements['before']['final'], measurements['after']['final']
                    assert before['overflow'] == after['overflow'], (filename, width, 'new overflow')
                    assert len(before['boxes']) == len(after['boxes'])
                    differences = [(b, a) for b, a in zip(before['boxes'], after['boxes']) if any(abs(b[k] - a[k]) > 1 for k in ['x', 'y', 'width', 'height'])]
                    if differences:
                        print(json.dumps(differences[:12]), flush=True)
                    for b, a in zip(before['boxes'], after['boxes']):
                        assert b['crop'] == a['crop'] and b['position'] == a['position'], (filename, width, b, a)
                        for key in ['x', 'y', 'width', 'height']:
                            assert abs(b[key] - a[key]) <= 1, (filename, width, key, b, a)
                    results.append({'page': filename, 'viewport': [width, height, dpr], **measurements})
                    print(f'PASS {filename} {width}px DPR {dpr}', flush=True)
            browser.close()
    finally:
        server.shutdown()
        report_name = 'layout-results-' + '-'.join(Path(name).stem for name in sys.argv[1:]) + '.json' if sys.argv[1:] else 'layout-results.json'
        (REPORT / report_name).write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(f'Passed {len(results)} before/after layout pairs; original files and SEO verified.')

if __name__ == '__main__':
    run()

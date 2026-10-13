"""Add responsive WebP sources while preserving each original image fallback."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
WIDTHS = {
    'hero-workflow-code': [400, 640, 800, 1200, 1672],
    'slavica-portrait-enhanced': [400, 640, 800, 1200, 1254],
    'screenshot_website': [1788],
    'screenshot_app': [1161],
    'tutor_notebook_java': [1890],
    'tutor_notebook_react': [1847],
}
HERO = '(max-width: 640px) calc(100vw - 61.2px), (max-width: 900px) calc(100vw - 66px), (max-width: 1152px) calc(44vw - 65.68px), 441.2px'
PORTRAIT = '(max-width: 900px) calc(100vw - 66px), (max-width: 1152px) calc(41vw - 56.96px), 415.36px'
CASE_HERO = '(max-width: 640px) calc(100vw - 66px), (max-width: 900px) calc(100vw - 82px), (max-width: 1152px) calc(57.5vw - 61.8px), 600.6px'
CASE_DETAIL = '(max-width: 640px) calc(100vw - 66px), (max-width: 900px) calc(100vw - 82px), (max-width: 1152px) calc(47.5vw - 51.4px), 495.8px'
PROJECT = '(max-width: 900px) calc(100vw - 69.2px), (max-width: 1152px) calc(25vw - 57.2px), 230.8px'
WIDE_PROJECT = '(max-width: 1152px) calc(100vw - 69.2px), 1082.8px'
PAGES = ['index.html', 'projects.html', 'website-erstellung.html', 'website-wartung.html', 'seo-optimierung.html', 'google-unternehmensprofil.html']

for filename in PAGES:
    path = ROOT / filename
    raw = path.read_bytes()
    text = raw.decode('utf-8')
    # Unwrap sources first so regenerated variant lists can be applied safely.
    text = re.sub(r'<picture style="display: (?:block|contents);"><source[^>]+>(<img[^>]+>)</picture>', r'\1', text)
    counts = {}
    def replace(match):
        img = match.group(0)
        name = re.search(r'src="([^"]+)\.png"', img).group(1)
        if name not in WIDTHS:
            return img
        counts[name] = counts.get(name, 0) + 1
        if filename == 'index.html':
            sizes = {'hero-workflow-code': HERO, 'slavica-portrait-enhanced': PORTRAIT,
                     'screenshot_app': CASE_HERO, 'tutor_notebook_react': CASE_DETAIL}[name]
        elif filename == 'projects.html':
            sizes = PROJECT
            # Only the first card can be initially visible on mobile.
            if name != 'screenshot_website' and 'loading=' not in img:
                img = img[:-1] + ' loading="lazy">'
        else:
            sizes = WIDE_PROJECT if filename == 'website-erstellung.html' and counts[name] > 1 else HERO
        if filename != 'projects.html' and 'loading=' not in img:
            img = img[:-1] + ' loading="eager">'
        # Local Chrome PerformanceObserver confirmed the homepage hero as LCP.
        if filename == 'index.html' and name == 'hero-workflow-code' and 'fetchpriority=' not in img:
            img = img[:-1] + ' fetchpriority="high">'
        # The original hero img was positioned by .hero-card > *.
        # A boxless picture keeps grid stretching and image heights unchanged.
        if sizes == HERO and 'style=' not in img:
            img = img[:-1] + ' style="position: relative;">'
        srcset = ', '.join(f'images/optimized/{name}-{width}.webp {width}w' for width in WIDTHS[name])
        return f'<picture style="display: contents;"><source style="display: none;" type="image/webp" srcset="{srcset}" sizes="{sizes}">{img}</picture>'
    text = re.sub(r'<img\b[^>]*src="[^"]+\.png"[^>]*>', replace, text)
    path.write_bytes(text.encode('utf-8'))
    print(filename, counts)

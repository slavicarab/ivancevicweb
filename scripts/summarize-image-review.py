"""Write a local review report and compact before/after visual comparisons."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'performance-review'
manifest = json.loads((ROOT / 'images/optimized/manifest.json').read_text())
results = json.loads((REPORT / 'layout-results-index.json').read_text())
rows = ['| Image | Original KiB | WebP variants (width: KiB) |', '|---|---:|---|']
for name, spec in manifest.items():
    variants = ', '.join(f"{v['width']}: {v['bytes']/1024:.1f}" for v in spec['variants'])
    rows.append(f"| {name}.png | {spec['source_bytes']/1024:.1f} | {variants} |")
home_names = ['hero-workflow-code', 'slavica-portrait-enhanced', 'screenshot_app', 'tutor_notebook_react']
original_home = sum(manifest[name]['source_bytes'] for name in home_names)
mobile = next(r for r in results if r['viewport'] == [390, 844, 2])
by_file = {Path(v['path']).name: v['bytes'] for spec in manifest.values() for v in spec['variants']}
optimized_home = sum(by_file[img['src'].split('/')[-1]] for img in mobile['after']['final']['images'])
all_original = sum(spec['source_bytes'] for spec in manifest.values())
all_full = sum(spec['variants'][-1]['bytes'] for spec in manifest.values())
text = f'''# Phase 1 image optimization — local review

No deployment or server changes have been performed. Original PNG files, CSS,
JavaScript, SEO content, metadata, canonical URLs, sitemap and robots.txt are unchanged.

## Files

Updated image markup in index.html, projects.html, website-erstellung.html,
website-wartung.html, seo-optimierung.html and google-unternehmensprofil.html.
Added 14 WebP files and manifest.json in images/optimized/.
Added reproducible generation, markup, browser-check and report scripts in scripts/.
This directory contains local test evidence and previews, not deployment assets.

## Image sizes

{chr(10).join(rows)}

Hero and portrait use responsive width variants. All four screenshots retain
their original resolution and use lossless WebP; decoded RGB pixels match their
originals exactly. Source PNGs remain as picture fallbacks.

## Bandwidth estimates

At a 390px viewport with DPR 2, Chrome selected the 800px hero and portrait.
Hero plus portrait: 3,084,599 → 83,696 bytes, saving 3,000,903 bytes (97.3%).
All four homepage images, after scrolling: {original_home:,} → {optimized_home:,} bytes,
saving {original_home-optimized_home:,} bytes ({(1-optimized_home/original_home)*100:.1f}%).
This includes below-the-fold screenshots; it is not a claim about initial-load payload.
Across six unique originals at full resolution: {all_original:,} → {all_full:,} bytes,
saving {all_original-all_full:,} bytes ({(1-all_full/all_original)*100:.1f}%).
These estimates exclude headers, unchanged assets and repeat-visit caching.
Variant choice depends on viewport, device pixel ratio and browser decisions.

## Validation

- 42 before/after browser layout comparisons across six pages.
- Widths: 375, 390, 640, 900, 901 and 1440 pixels; DPR 1, 2 and 3 as applicable.
- 14 targeted comparisons after selecting full-resolution project screenshots.
- 7 final homepage comparisons after adding LCP fetch priority.
- Matching section, image, heading and cookie-banner geometry within 1 CSS pixel;
  matching object-fit and object-position; no new horizontal overflow.
- Image decoding and browser-selected sources checked after scrolling.
- Cookie settings, save, reject, reopen and saved rejection across reload checked.
- Existing consent and service-page Node checks passed; git diff --check passed.
- Original image bytes and unrelated CSS/JS/SEO files checked against Git HEAD.
- Removing image-delivery markup reproduces original HTML exactly.
- Full-resolution lossless screenshots verified pixel for pixel.
- Hero and portrait visuals inspected; compact comparisons are saved alongside this report.

## LCP and remaining limits

Local Chrome PerformanceObserver identified the homepage hero as LCP at all tested
viewports, including both mobile widths, with the consent banner present.
Only that confirmed homepage image has fetchpriority="high"; it remains eager.
Existing homepage lazy loading is preserved. The second and third project cards
now use native lazy loading. No preload was added.

Local unthrottled timings do not reproduce the reported 11-second production LCP
and are not a new Lighthouse score. Production PageSpeed validation remains pending
deployment approval. Native lazy loading can still fetch nearby offscreen images.
Hero and portrait compression is lossy; original assets remain available.
Caching policy is unchanged and remains a separate future phase.
Browser coverage is Chrome; Safari/Firefox have not been tested.
Analytics network requests were blocked in browser tests; consent state behavior
was tested locally and by the existing consent suite.

Wait for explicit deployment approval before copying website files to production.
'''
(REPORT / 'phase-1-report.md').write_text(text, encoding='utf-8')

for width, dpr in [(390, 2), (1440, 1), (1440, 2)]:
    result = next(r for r in results if r['viewport'][0] == width and r['viewport'][2] == dpr)
    before = Image.open(REPORT / f'home-{width}-{dpr}-before.png').convert('RGB')
    after = Image.open(REPORT / f'home-{width}-{dpr}-after.png').convert('RGB')
    # Extract actual rendered image regions to assess crops and compression side by side.
    panels = []
    for index in range(2):
        box = [b for b in result['after']['final']['boxes'] if b['tag'] == 'IMG'][index]
        bounds = tuple(round(value * dpr) for value in [box['x'], box['y'], box['x']+box['width'], box['y']+box['height']])
        pair = []
        for snapshot in [before, after]:
            crop = snapshot.crop(bounds)
            crop.thumbnail((600, 650), Image.Resampling.LANCZOS)
            pair.append(crop)
        canvas = Image.new('RGB', (pair[0].width * 2, max(im.height for im in pair) + 30), '#ffffff')
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 8), 'Original', fill='black')
        draw.text((pair[0].width + 8, 8), 'WebP', fill='black')
        canvas.paste(pair[0], (0, 30))
        canvas.paste(pair[1], (pair[0].width, 30))
        panels.append(canvas)
    montage = Image.new('RGB', (max(p.width for p in panels), sum(p.height for p in panels)), '#ffffff')
    y = 0
    for panel in panels:
        montage.paste(panel, (0, y))
        y += panel.height
    montage.save(REPORT / f'comparison-{width}-dpr{dpr}.jpg', quality=95, subsampling=0)
print('Wrote performance-review/phase-1-report.md and three visual comparisons.')

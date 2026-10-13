"""Generate Phase 1 WebP assets without modifying the source PNG files.

Requires Pillow. Run from the repository root.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "images" / "optimized"
SPECS = {
    "hero-workflow-code": ([400, 640, 800, 1200, 1672], False, 88),
    "slavica-portrait-enhanced": ([400, 640, 800, 1200, 1254], False, 90),
    "screenshot_website": ([1788], True, 100),
    "screenshot_app": ([1161], True, 100),
    "tutor_notebook_java": ([1890], True, 100),
    "tutor_notebook_react": ([1847], True, 100),
}

def generate():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, (widths, lossless, quality) in SPECS.items():
        source = ROOT / f"{name}.png"
        with Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            variants = []
            for width in widths:
                height = round(image.height * width / image.width)
                resized = image.resize((width, height), Image.Resampling.LANCZOS)
                destination = OUTPUT / f"{name}-{width}.webp"
                options = dict(format="WEBP", lossless=lossless, quality=quality, method=6)
                if image.info.get("icc_profile"):
                    options["icc_profile"] = image.info["icc_profile"]
                resized.save(destination, **options)
                variants.append(dict(path=destination.relative_to(ROOT).as_posix(),
                                     width=width, height=height, bytes=destination.stat().st_size))
            report[name] = dict(source_bytes=source.stat().st_size,
                                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                dimensions=list(image.size), lossless=lossless, variants=variants)
    (OUTPUT / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    generate()

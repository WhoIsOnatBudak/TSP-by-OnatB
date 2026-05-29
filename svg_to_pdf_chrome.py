#!/usr/bin/env python3

import re
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_svg_size(svg_text):
    svg_tag_match = re.search(r"<svg\b[^>]*>", svg_text)

    if not svg_tag_match:
        raise ValueError("SVG tag not found")

    svg_tag = svg_tag_match.group(0)

    width_match = re.search(r'\bwidth="([0-9.]+)', svg_tag)
    height_match = re.search(r'\bheight="([0-9.]+)', svg_tag)

    if width_match and height_match:
        return float(width_match.group(1)), float(height_match.group(1))

    view_box_match = re.search(r'\bviewBox="[^"]*?([0-9.]+)\s+([0-9.]+)"', svg_tag)

    if view_box_match:
        return float(view_box_match.group(1)), float(view_box_match.group(2))

    raise ValueError("SVG width/height or viewBox not found")


def make_html(svg_text, width, height):
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
  size: {width}px {height}px;
  margin: 0;
}}
html, body {{
  margin: 0;
  padding: 0;
  width: {width}px;
  height: {height}px;
  background: white;
}}
svg {{
  display: block;
  width: {width}px;
  height: {height}px;
}}
</style>
</head>
<body>
{svg_text}
</body>
</html>
"""


def convert_one(chrome, svg_path, pdf_path):
    svg_text = svg_path.read_text(encoding="utf-8")
    width, height = parse_svg_size(svg_text)
    html = make_html(svg_text, width, height)

    with tempfile.TemporaryDirectory() as temp_dir:
        html_path = Path(temp_dir) / f"{svg_path.stem}.html"
        profile_path = Path(temp_dir) / "chrome-profile"
        home_path = Path(temp_dir) / "home"
        config_path = Path(temp_dir) / "config"
        cache_path = Path(temp_dir) / "cache"
        html_path.write_text(html, encoding="utf-8")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        home_path.mkdir()
        config_path.mkdir()
        cache_path.mkdir()
        env = os.environ.copy()
        env.update({
            "HOME": str(home_path),
            "XDG_CONFIG_HOME": str(config_path),
            "XDG_CACHE_HOME": str(cache_path),
        })

        subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-crash-reporter",
                "--disable-extensions",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile_path}",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ],
            check=True,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Rapor/ImagesCSV")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Rapor/ImagesPDF")
    chrome = sys.argv[3] if len(sys.argv) > 3 else "google-chrome"
    svg_paths = sorted(input_dir.glob("*.svg"))

    if not svg_paths:
        raise ValueError(f"No SVG files found in {input_dir}")

    for svg_path in svg_paths:
        pdf_path = output_dir / f"{svg_path.stem}.pdf"
        convert_one(chrome, svg_path, pdf_path)
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()

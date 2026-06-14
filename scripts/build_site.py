"""Build static site for GitHub Pages.

Simply copies the site/ directory to _site/.
No backend dependency — this is a project showcase, not a live app.
"""

import shutil
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
OUTPUT_DIR = Path(__file__).parent.parent / "_site"


def main():
    print("=" * 40)
    print("  Urban Pulse — Static Site Builder")
    print("=" * 40)

    # Clean and copy
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    shutil.copytree(SITE_DIR, OUTPUT_DIR)

    # Copy favicon if exists
    favicon = Path(__file__).parent.parent / "frontend" / "favicon.ico"
    if favicon.exists():
        shutil.copy2(favicon, OUTPUT_DIR / "favicon.ico")

    print(f"  ✓ Copied {SITE_DIR} → {OUTPUT_DIR}")
    print(f"  ✓ Files: {len(list(OUTPUT_DIR.rglob('*')))}")
    print()
    print("  Deployment: _site/ → GitHub Pages")
    print()


if __name__ == "__main__":
    main()

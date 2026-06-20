"""Build static site for GitHub / GitCode Pages.

Copies the latest frontend/ application to _site/.
No backend dependency.
"""

import shutil
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
OUTPUT_DIR = Path(__file__).parent.parent / "_site"


def main():
    print("=" * 40)
    print("  Urban Pulse — Static Site Builder")
    print("=" * 40)

    if not FRONTEND_DIR.exists():
        raise FileNotFoundError(f"Frontend directory not found: {FRONTEND_DIR}")

    # Clean and copy
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    shutil.copytree(FRONTEND_DIR, OUTPUT_DIR)

    print(f"  ✓ Copied {FRONTEND_DIR} → {OUTPUT_DIR}")
    print(f"  ✓ Files: {len(list(OUTPUT_DIR.rglob('*')))}")
    print()
    print("  Deployment: _site/ → GitHub Pages / GitCode Pages")
    print()


if __name__ == "__main__":
    main()

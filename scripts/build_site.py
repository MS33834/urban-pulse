"""Build static site for GitHub / GitCode Pages.

Copies the latest frontend/ application to _site/.
No backend dependency.
"""

import shutil
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
OUTPUT_DIR = Path(__file__).parent.parent / "_site"
PUBLIC_DIR = Path(__file__).parent.parent / "public"


def _sync_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main():
    print("=" * 40)
    print("  Urban Pulse — Static Site Builder")
    print("=" * 40)

    if not FRONTEND_DIR.exists():
        raise FileNotFoundError(f"Frontend directory not found: {FRONTEND_DIR}")

    # Clean and copy to both _site/ (GitHub Pages) and public/ (GitCode Pages)
    _sync_dir(FRONTEND_DIR, OUTPUT_DIR)
    _sync_dir(FRONTEND_DIR, PUBLIC_DIR)

    print(f"  ✓ Copied {FRONTEND_DIR} → {OUTPUT_DIR}")
    print(f"  ✓ Copied {FRONTEND_DIR} → {PUBLIC_DIR}")
    print(f"  ✓ Files: {len(list(OUTPUT_DIR.rglob('*')))}")
    print()
    print("  Deployment: _site/ → GitHub Pages / GitCode Pages")
    print()


if __name__ == "__main__":
    main()

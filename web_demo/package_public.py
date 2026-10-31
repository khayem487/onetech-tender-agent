"""Create a new, allowlisted public deployment directory; never copy runtime data.

Run from the repository: python web_demo/package_public.py /new/empty/destination
The original CLI pyproject and private/local services are intentionally excluded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil


def package(destination: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    destination = destination.resolve()
    if destination == root or root.is_relative_to(destination):
        raise ValueError("Choose a new deployment directory outside the repository")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("The deployment directory must be new or empty; no files are deleted")
    destination.mkdir(parents=True, exist_ok=True)
    sources = [root / name for name in ("app.py", "requirements.txt", "vercel.json", ".python-version")]
    sources += sorted((root / "src" / "onetech_ao").glob("*.py"))
    sources += sorted((root / "web_demo").glob("*.py"))
    sources += sorted((root / "web_demo" / "templates").glob("*.html"))
    sources += sorted((root / "web_demo" / "static").glob("*.js"))
    sources += sorted((root / "web_demo" / "static").glob("*.css"))
    copied = []
    for source in sources:
        if source.is_symlink() or not source.is_file():
            raise ValueError("Only regular, explicitly selected source files may be packaged")
        relative = source.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append(relative.as_posix())
        if relative.parent == Path("web_demo/static"):
            cdn = destination / "public" / "static" / source.name
            cdn.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, cdn)
            copied.append(cdn.relative_to(destination).as_posix())
    (destination / ".vercelignore").write_text(".git\n.vercel\n.env*\n**/__pycache__\n**/*.pyc\n", encoding="utf-8")
    return {"destination": str(destination), "files": copied, "dependency_manifest": "requirements.txt"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.destination), indent=2))


if __name__ == "__main__":
    main()

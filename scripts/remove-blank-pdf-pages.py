"""Remove accidental textless pages created by a browser print layout."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--min-text", type=int, default=10)
    args = parser.parse_args()

    document = fitz.open(args.pdf)
    blank_indexes = [
        index
        for index, page in enumerate(document)
        if len(page.get_text("text").strip()) < args.min_text and not page.get_images()
    ]
    if not blank_indexes:
        print("no_blank_pages")
        return

    cleaned = args.pdf.with_name(args.pdf.stem + ".cleaned.pdf")
    for index in reversed(blank_indexes):
        document.delete_page(index)
    document.save(cleaned, garbage=4, deflate=True)
    document.close()
    cleaned.replace(args.pdf)
    print("removed_pages=" + ",".join(str(index + 1) for index in blank_indexes))


if __name__ == "__main__":
    main()

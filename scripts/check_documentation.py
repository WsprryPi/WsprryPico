#!/usr/bin/env python3
"""Validate maintained Markdown targets and the built operator site's links.

Run with docs/.venv/bin/python after a strict Sphinx HTML build.
Historical source-coordinate text and external links are not rewritten here.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
parser = MarkdownIt()


def slug(text):
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def markdown_ids(path):
    tokens = parser.parse(path.read_text())
    ids, counts = set(), {}
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            name = slug(tokens[i + 1].content.replace("`", ""))
            occurrence = counts.get(name, 0)
            counts[name] = occurrence + 1
            ids.add(name + (f"-{occurrence}" if occurrence else ""))
    return ids


class HTML(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links = set(), []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag in ("a", "img", "script", "link"):
            target = attrs.get("href") or attrs.get("src")
            if target:
                self.links.append(target)


def main():
    errors, checked = [], 0
    sources = [*ROOT.glob("*.md"), *ROOT.glob("engineering/**/*.md"),
               *ROOT.glob("src/**/README.md"), *ROOT.glob("tests/**/README.md")]
    sources = [p for p in sources if "node_modules" not in p.parts]
    for source in sources:
        for token in parser.parse(source.read_text()):
            for child in token.children or []:
                if child.type not in ("link_open", "image"):
                    continue
                reference = child.attrGet("href") or child.attrGet("src")
                target = urlsplit(reference)
                if target.scheme or target.netloc:
                    continue
                path = (source.parent / unquote(target.path)).resolve() if target.path else source
                checked += 1
                if not path.exists():
                    errors.append(f"{source.relative_to(ROOT)}: missing {reference}")
                elif target.fragment and path.suffix == ".md" and unquote(target.fragment) not in markdown_ids(path):
                    errors.append(f"{source.relative_to(ROOT)}: missing anchor {reference}")
    built = ROOT / "docs/_build/html"
    pages = {p.resolve(): HTML(p.read_text()) for p in built.rglob("*.html")}
    for path, page in pages.items():
        for reference in page.links:
            target = urlsplit(reference)
            if target.scheme or target.netloc:
                continue
            destination = (path.parent / unquote(target.path)).resolve() if target.path else path
            if destination.is_dir():
                destination /= "index.html"
            checked += 1
            if not destination.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing {reference}")
            elif target.fragment and destination in pages and unquote(target.fragment) not in pages[destination].ids:
                # The accessibility script creates this skip target after load.
                if target.fragment != "main-content":
                    errors.append(f"{path.relative_to(ROOT)}: missing anchor {reference}")
    if not pages:
        errors.append("No built HTML; build the operator manual first")
    # Firmware URLs are external to the device but owned by this manual. Check
    # their emitted destinations here instead of skipping them as external links.
    from check_contextual_help import emitted_links, validate
    try:
        validate(emitted_links(), built)
    except (ValueError, OSError) as error:
        errors.append(str(error))
    for error in errors:
        print(error)
    print(f"Checked {len(sources)} Markdown sources, {len(pages)} HTML pages, {checked} local targets; {len(errors)} errors")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())

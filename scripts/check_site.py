#!/usr/bin/env python3
"""Dependency-free structural checks for the Loop Alarm static site."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT
PUBLIC_BASE = "https://jamesc0ry.github.io/loop-alarm-site/"
EXPECTED = {
    Path("index.html"): (
        "Loop Alarm - Apple Watch reminders",
        PUBLIC_BASE,
    ),
    Path("privacy/index.html"): (
        "Privacy Policy - Loop Alarm",
        f"{PUBLIC_BASE}privacy/",
    ),
    Path("support/index.html"): (
        "Support - Loop Alarm",
        f"{PUBLIC_BASE}support/",
    ),
}
APPROVED_EMAIL = "loopalarm.help@outlook.com"
APPROVED_MAILTO = f"mailto:{APPROVED_EMAIL}"
OLD_CONTACT_PLACEHOLDER = "Support contact will be added before public launch."
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
STALE_PUBLIC_MARKERS = (
    r"private preview",
    r"\bunpublished\b",
    r"not yet published",
    r"eventually published",
    r"not yet (?:an )?authorized",
    r"custom-hourly-reminders",
)
TRACKER_MARKERS = (
    r"googletagmanager",
    r"google-analytics",
    r"\bgtag\s*\(",
    r"\bga\s*\(",
    r"\bfbq\s*\(",
    r"\bplausible\s*\(",
    r"\bposthog",
    r"\bmixpanel",
    r"\bsegment\s*\.com",
    r"tracking[-_ ]?pixel",
)
CONTACT_MARKERS = (
    r"(?<!\d)(?:\+?1[-. ]?)?(?:\(\d{3}\)|\d{3})[-. ]\d{3}[-. ]\d{4}(?!\d)",
    r"\b(?:street|st\.|road|rd\.|avenue|ave\.|lane|ln\.|drive|dr\.|boulevard|blvd\.|suite|po box)\b",
    r"\b(?:zip code|postal code)\b",
    r"\b\d{5}(?:-\d{4})?\b",
)
ALLOWED_EXTERNAL_SCHEMES = {"https", "mailto"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        self.tags.append((tag, values))
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self.in_title:
            self.title_parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()


def fail(errors: list[str], page: Path | str, message: str) -> None:
    errors.append(f"{page}: {message}")


def resolve_internal(page: Path, href: str, site: Path = SITE) -> tuple[Path, str] | None:
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return None
    if href.startswith("/"):
        raise ValueError("root-relative URLs break at the GitHub project Pages base path")

    raw_path = unquote(parsed.path)
    target = site / page if not raw_path else site / page.parent / raw_path
    target = target.resolve()
    resolved_site = site.resolve()
    if resolved_site not in target.parents and target != resolved_site:
        raise ValueError("link escapes the site directory")
    if raw_path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target, unquote(parsed.fragment)


def attribute_values(parser: PageParser, tag_name: str, attribute: str) -> list[str]:
    return [attrs.get(attribute, "") for tag, attrs in parser.tags if tag == tag_name]


def has_meta(parser: PageParser, key: str, value: str) -> bool:
    return any(tag == "meta" and attrs.get(key) == value for tag, attrs in parser.tags)


def check_site(site: Path = SITE) -> list[str]:
    site = site.resolve()
    errors: list[str] = []
    pages: dict[Path, PageParser] = {}
    sources: dict[Path, str] = {}

    for path in sorted(site.rglob("*.html")):
        if any(part.startswith(".") for part in path.relative_to(site).parts):
            continue
        relative = path.relative_to(site)
        source = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(source)
        pages[relative] = parser
        sources[relative] = source

    for relative in EXPECTED:
        if relative not in pages:
            fail(errors, relative, "required file is missing")

    for relative, parser in pages.items():
        expected = EXPECTED.get(relative)
        source = sources[relative]

        if expected is not None:
            expected_title, expected_canonical = expected
            if parser.title != expected_title:
                fail(errors, relative, f"expected title {expected_title!r}, found {parser.title!r}")

        tag_names = [tag for tag, _ in parser.tags]
        if tag_names.count("h1") != 1:
            fail(errors, relative, "must contain exactly one h1")
        for forbidden in ("script", "form", "iframe"):
            if forbidden in tag_names:
                fail(errors, relative, f"unexpected <{forbidden}> element")

        html_languages = [attrs.get("lang") for tag, attrs in parser.tags if tag == "html"]
        if html_languages != ["en"]:
            fail(errors, relative, "must declare exactly one <html lang=\"en\">")
        if not has_meta(parser, "charset", "utf-8"):
            fail(errors, relative, "missing UTF-8 charset metadata")
        if not any(
            tag == "meta"
            and attrs.get("name") == "viewport"
            and attrs.get("content") == "width=device-width, initial-scale=1"
            for tag, attrs in parser.tags
        ):
            fail(errors, relative, "missing responsive viewport metadata")
        if not any(
            tag == "meta" and attrs.get("name") == "description" and attrs.get("content")
            for tag, attrs in parser.tags
        ):
            fail(errors, relative, "missing page description metadata")
        if "main-content" not in parser.ids:
            fail(errors, relative, "main content must expose id=\"main-content\"")
        if not any(
            tag == "a"
            and attrs.get("class") == "skip-link"
            and attrs.get("href") == "#main-content"
            for tag, attrs in parser.tags
        ):
            fail(errors, relative, "missing skip link to main content")

        canonical_links = [
            attrs.get("href", "")
            for tag, attrs in parser.tags
            if tag == "link" and "canonical" in attrs.get("rel", "").split()
        ]
        if expected is not None and canonical_links != [expected_canonical]:
            fail(
                errors,
                relative,
                f"expected one canonical URL {expected_canonical!r}, found {canonical_links!r}",
            )
        elif expected is None and len(canonical_links) != 1:
            fail(errors, relative, "must contain exactly one canonical URL")

        for tag, attrs in parser.tags:
            source_url = attrs.get("src")
            if source_url:
                parsed_source = urlparse(source_url)
                if parsed_source.scheme or parsed_source.netloc:
                    fail(errors, relative, f"unexpected external asset: {source_url}")
                else:
                    _check_local_reference(errors, pages, relative, source_url, site, "asset")

            if tag == "link" and set(attrs.get("rel", "").split()) & {"icon", "stylesheet"}:
                resource = attrs.get("href", "")
                parsed_resource = urlparse(resource)
                if parsed_resource.scheme or parsed_resource.netloc:
                    fail(errors, relative, f"unexpected external resource: {resource}")
                else:
                    _check_local_reference(errors, pages, relative, resource, site, "resource")

        for href in parser.links:
            parsed = urlparse(href)
            if parsed.scheme == "mailto":
                if href != APPROVED_MAILTO:
                    fail(errors, relative, f"unexpected contact link: {href}")
                continue
            if parsed.scheme or parsed.netloc:
                if parsed.scheme not in ALLOWED_EXTERNAL_SCHEMES:
                    fail(errors, relative, f"unsafe external link scheme: {href}")
                continue
            _check_local_reference(errors, pages, relative, href, site, "link")

        for destination in (site / "privacy/index.html", site / "support/index.html"):
            discovered = False
            for href in parser.links:
                try:
                    resolved = resolve_internal(relative, href, site)
                except ValueError:
                    continue
                if resolved is not None and resolved[0] == destination:
                    discovered = True
                    break
            if not discovered:
                fail(errors, relative, f"does not link to {destination.relative_to(site)}")

        for email in EMAIL_PATTERN.findall(source):
            if email != APPROVED_EMAIL:
                fail(errors, relative, f"unapproved email address: {email}")
        if APPROVED_EMAIL not in parser.text:
            fail(errors, relative, "must name the approved email address")
        if APPROVED_MAILTO not in parser.links:
            fail(errors, relative, "must link directly to the approved email address")
        if OLD_CONTACT_PLACEHOLDER in source:
            fail(errors, relative, "old support contact placeholder found")
        if re.search(r"\b(?:TODO|TBD|example\.(?:com|org|net))\b", source, re.IGNORECASE):
            fail(errors, relative, "unapproved placeholder content found")
        for marker in STALE_PUBLIC_MARKERS:
            if re.search(marker, source, re.IGNORECASE):
                fail(errors, relative, f"stale pre-publication wording: {marker}")
        for marker in TRACKER_MARKERS:
            if re.search(marker, source, re.IGNORECASE):
                fail(errors, relative, f"unexpected tracker marker: {marker}")
        for marker in CONTACT_MARKERS:
            if re.search(marker, source, re.IGNORECASE):
                fail(errors, relative, f"unexpected contact detail: {marker}")

    privacy = pages.get(Path("privacy/index.html"))
    if privacy:
        for required in (
            "Effective August 12, 2026",
            "does not collect personal data",
            "does not share or sell data",
            "local Apple Watch storage",
            "hosted with GitHub Pages",
            "logs visitors' IP addresses for security purposes",
        ):
            if required not in privacy.text:
                fail(errors, "privacy/index.html", f"missing required policy statement: {required!r}")

    support = pages.get(Path("support/index.html"))
    if support and "Email us for help with Loop Alarm." not in support.text:
        fail(errors, "support/index.html", "missing public support availability statement")

    stylesheet = site / "styles.css"
    if not stylesheet.is_file():
        fail(errors, "styles.css", "required stylesheet is missing")
    else:
        stylesheet_source = stylesheet.read_text(encoding="utf-8")
        if re.search(r"@import\s+(?:url\(\s*)?['\"]?(?:https?:)?//", stylesheet_source, re.IGNORECASE):
            fail(errors, "styles.css", "unexpected external stylesheet import")
        if re.search(r"url\(\s*['\"]?(?:https?:)?//", stylesheet_source, re.IGNORECASE):
            fail(errors, "styles.css", "unexpected external asset URL")

    for required_file in ("favicon.svg", ".nojekyll", "robots.txt", "sitemap.xml"):
        if not (site / required_file).is_file():
            fail(errors, required_file, "required file is missing")

    expected_urls = {canonical for _, canonical in EXPECTED.values()}
    sitemap = site / "sitemap.xml"
    if sitemap.is_file():
        sitemap_urls = set(re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8")))
        if sitemap_urls != expected_urls:
            fail(errors, "sitemap.xml", f"expected public URLs {sorted(expected_urls)!r}")
    robots = site / "robots.txt"
    if robots.is_file():
        expected_sitemap = f"Sitemap: {PUBLIC_BASE}sitemap.xml"
        if expected_sitemap not in robots.read_text(encoding="utf-8"):
            fail(errors, "robots.txt", f"missing {expected_sitemap!r}")

    return errors


def _check_local_reference(
    errors: list[str],
    pages: dict[Path, PageParser],
    page: Path,
    reference: str,
    site: Path,
    kind: str,
) -> None:
    try:
        resolved = resolve_internal(page, reference, site)
    except ValueError as error:
        fail(errors, page, f"invalid {kind} {reference!r}: {error}")
        return
    if resolved is None:
        return
    target, fragment = resolved
    if not target.is_file():
        fail(errors, page, f"broken internal {kind} {reference!r}")
        return
    if fragment:
        try:
            target_relative = target.relative_to(site)
        except ValueError:
            fail(errors, page, f"invalid fragment target {reference!r}")
            return
        target_page = pages.get(target_relative)
        if target_page is None or fragment not in target_page.ids:
            fail(errors, page, f"broken fragment in {kind} {reference!r}")


def main() -> int:
    errors = check_site()

    if errors:
        print("Loop Alarm site checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Loop Alarm site checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

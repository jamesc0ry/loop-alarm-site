from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import check_site


SITE_FILES = (
    Path("index.html"),
    Path("privacy/index.html"),
    Path("styles.css"),
    Path("contact.js"),
    Path("favicon.svg"),
    Path(".nojekyll"),
    Path("robots.txt"),
    Path("sitemap.xml"),
)


class CheckSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.site = Path(self.temporary_directory.name) / "site"
        self.site.mkdir()
        for relative in SITE_FILES:
            destination = self.site / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(check_site.SITE / relative, destination)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def replace(self, relative: str, old: str, new: str) -> None:
        path = self.site / relative
        path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def assert_has_error(self, errors: list[str], message: str) -> None:
        self.assertTrue(
            any(message in error for error in errors),
            f"expected an error containing {message!r}, found {errors!r}",
        )

    def test_public_site_passes(self) -> None:
        self.assertEqual(check_site.check_site(self.site), [])

    def test_old_placeholder_and_stale_preview_are_rejected(self) -> None:
        self.replace(
            "privacy/index.html",
            "For privacy questions",
            f"{check_site.OLD_CONTACT_PLACEHOLDER} Private preview.",
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "old support contact placeholder found")
        self.assert_has_error(errors, "stale pre-publication wording")

    def test_private_project_subpath_is_rejected(self) -> None:
        self.replace("index.html", "Interface annotations", "custom-hourly-reminders annotations")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "stale pre-publication wording")

    def test_guessed_contact_is_rejected(self) -> None:
        self.replace("index.html", check_site.APPROVED_EMAIL, "support@loopalarm.co")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unapproved email address: support@loopalarm.co")
        self.assert_has_error(errors, "unexpected contact link: mailto:support@loopalarm.co")

    def test_modified_mailto_is_rejected(self) -> None:
        self.replace(
            "index.html",
            check_site.APPROVED_SUPPORT_MAILTO,
            f"{check_site.APPROVED_MAILTO}?subject=Help",
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unexpected contact link")
        self.assert_has_error(errors, "information screen email must match the app support link")

    def test_root_relative_link_is_rejected(self) -> None:
        self.replace("index.html", 'href="privacy/#contact"', 'href="/privacy/#contact"')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "root-relative URLs break at the GitHub project Pages base path")

    def test_broken_internal_link_is_rejected(self) -> None:
        self.replace("index.html", 'href="privacy/#contact"', 'href="missing/#contact"')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "broken internal link 'missing/#contact'")

    def test_unlisted_html_page_links_are_checked(self) -> None:
        extra_page = self.site / "unlisted.html"
        shutil.copyfile(self.site / "index.html", extra_page)

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unexpected public HTML route")

    def test_removed_support_route_is_rejected(self) -> None:
        support_page = self.site / "support/index.html"
        support_page.parent.mkdir()
        shutil.copyfile(self.site / "privacy/index.html", support_page)

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "support/index.html: unexpected public HTML route")

    def test_homepage_requires_the_annotated_watch_contract(self) -> None:
        self.replace("index.html", "annotation-toggle", "missing-toggle-annotation")
        self.replace(
            "index.html",
            'class="interval-dial" aria-hidden="true">45</div>',
            'class="interval-dial" aria-hidden="true"><button>45</button></div>',
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "expected exactly one .annotation-toggle")
        self.assert_has_error(errors, "static watch rendering must not contain <button>")

    def test_homepage_rejects_information_annotation_and_footer(self) -> None:
        self.replace(
            "index.html",
            '<ol class="annotations" aria-label="Interface annotations">',
            '<ol class="annotations" aria-label="Interface annotations"><li class="annotation-information">App information</li>',
        )
        self.replace("index.html", "</body>", "<footer>Loop Alarm</footer></body>")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "homepage must not contain an app information annotation")
        self.assert_has_error(errors, "homepage must not contain a footer")

    def test_connectors_must_be_single_straight_lines(self) -> None:
        self.replace(
            "index.html",
            '<line x1="194" y1="88" x2="349" y2="136"></line>',
            '<path d="M194 88 H270 L349 136"></path>',
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "connectors must contain exactly six straight SVG lines")

    def test_headers_must_link_directly_to_contact(self) -> None:
        self.replace("index.html", "Privacy/Contact", "Privacy")
        self.replace("privacy/index.html", 'href="#contact">Privacy/Contact', 'href="./">Privacy')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "header must link Privacy/Contact to privacy/#contact")
        self.assert_has_error(errors, "header must link Privacy/Contact to #contact")

    def test_contact_reveal_contract_is_enforced(self) -> None:
        self.replace("privacy/index.html", "data-contact", "missing-contact-hook")
        self.replace("privacy/index.html", "<noscript>", "<span>")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "contact reveal must expose one polite live region")
        self.assert_has_error(errors, "contact reveal must provide one no-JavaScript fallback")

    def test_privacy_page_must_not_expose_contact_before_activation(self) -> None:
        self.replace(
            "privacy/index.html",
            "For privacy questions, contact Loop Alarm Support:",
            f'For privacy questions, email <a href="{check_site.APPROVED_MAILTO}">{check_site.APPROVED_EMAIL}</a>:',
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "must not expose the contact address before activation")

    def test_contact_script_is_narrow_and_obfuscated(self) -> None:
        self.replace(
            "contact.js",
            'const address = ["pleh.mralapool", "moc.kooltuo"]',
            f'const address = "{check_site.APPROVED_EMAIL}"',
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "must not contain the plain contact address")

    def test_content_security_policies_are_page_specific(self) -> None:
        self.replace("index.html", "script-src 'none'", "script-src 'self'")
        self.replace("privacy/index.html", "script-src 'self'", "script-src 'unsafe-inline'")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "index.html: expected one exact content security policy")
        self.assert_has_error(errors, "privacy/index.html: expected one exact content security policy")

    def test_only_privacy_page_may_load_the_contact_script(self) -> None:
        self.replace("index.html", "</body>", '<script src="contact.js" defer></script></body>')
        self.replace("privacy/index.html", '<script src="../contact.js" defer></script>', "")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "index.html: expected approved scripts []")
        self.assert_has_error(errors, "privacy/index.html: expected approved scripts")

    def test_information_screen_contract_is_enforced(self) -> None:
        self.replace("index.html", "<details class=\"information-control\">", "<div class=\"information-control\">")
        self.replace("index.html", "</details>", "</div>")
        self.replace("index.html", check_site.PUBLIC_BASE, "https://example.org/")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "information control must be one native <details> disclosure")
        self.assert_has_error(errors, "information screen website must match the public app link")

    def test_connectors_must_stay_out_of_accessibility_tree(self) -> None:
        self.replace(
            "index.html",
            'class="connectors connectors-wide" viewBox="0 0 760 540" aria-hidden="true"',
            'class="connectors connectors-wide" viewBox="0 0 760 540" aria-hidden="false"',
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, ".connectors-wide must be a single hidden decorative connector")

    def test_broken_fragment_is_rejected(self) -> None:
        self.replace("privacy/index.html", 'href="#app-data"', 'href="#missing"')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "broken fragment in link '#missing'")

    def test_wrong_canonical_is_rejected(self) -> None:
        self.replace(
            "index.html",
            check_site.PUBLIC_BASE,
            "https://jamesc0ry.github.io/wrong-site/",
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "expected one canonical URL")

    def test_missing_accessibility_metadata_is_rejected(self) -> None:
        self.replace("index.html", ' lang="en"', "")
        self.replace("index.html", '<a class="skip-link" href="#main-content">Skip to content</a>', "")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "must declare exactly one <html lang=\"en\">")
        self.assert_has_error(errors, "missing skip link to main content")

    def test_remote_asset_is_rejected(self) -> None:
        self.replace("index.html", 'href="styles.css"', 'href="https://example.com/styles.css"')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unexpected external resource")


if __name__ == "__main__":
    unittest.main()

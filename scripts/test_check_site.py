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
    Path("support/index.html"),
    Path("styles.css"),
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
            "support/index.html",
            "Email us for help with Loop Alarm.",
            f"{check_site.OLD_CONTACT_PLACEHOLDER} Private preview.",
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "old support contact placeholder found")
        self.assert_has_error(errors, "stale pre-publication wording")

    def test_private_project_subpath_is_rejected(self) -> None:
        self.replace("index.html", "Loop Alarm features", "custom-hourly-reminders features")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "stale pre-publication wording")

    def test_guessed_contact_is_rejected(self) -> None:
        self.replace("support/index.html", check_site.APPROVED_EMAIL, "support@loopalarm.co")

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unapproved email address: support@loopalarm.co")
        self.assert_has_error(errors, "unexpected contact link: mailto:support@loopalarm.co")

    def test_modified_mailto_is_rejected(self) -> None:
        self.replace(
            "index.html",
            check_site.APPROVED_MAILTO,
            f"{check_site.APPROVED_MAILTO}?subject=Help",
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unexpected contact link")
        self.assert_has_error(errors, "must link directly to the approved email address")

    def test_root_relative_link_is_rejected(self) -> None:
        self.replace("index.html", 'href="support/"', 'href="/support/"')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "root-relative URLs break at the GitHub project Pages base path")

    def test_broken_internal_link_is_rejected(self) -> None:
        self.replace("index.html", 'href="support/"', 'href="missing/"')

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "broken internal link 'missing/'")

    def test_unlisted_html_page_links_are_checked(self) -> None:
        extra_page = self.site / "unlisted.html"
        shutil.copyfile(self.site / "index.html", extra_page)
        extra_page.write_text(
            extra_page.read_text(encoding="utf-8").replace('href="support/"', 'href="missing/"'),
            encoding="utf-8",
        )

        errors = check_site.check_site(self.site)

        self.assert_has_error(errors, "unlisted.html: broken internal link 'missing/'")

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
